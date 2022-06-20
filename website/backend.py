from aiohttp.web import HTTPFound, Request, Response, RouteTableDef, json_response
import aiohttp_session
from discord.ext import vbu


routes = RouteTableDef()


@routes.get("/login_processor")
async def login_processor(request: Request):
    """
    Page the discord login redirects the user to when successfully logged in with Discord.
    """

    # Process their login code
    v = await vbu.web.process_discord_login(request)

    # It failed - we want to redirect back to the index
    if isinstance(v, Response):
        return HTTPFound(location="/")

    # It succeeded - let's redirect them to where we specified to go if we
    # used a decorator, OR back to the index page
    session = await aiohttp_session.get_session(request)
    return HTTPFound(location=session.pop("redirect_on_login", "/"))


@routes.get("/logout")
async def logout(request: Request):
    """
    Destroy the user's login session.
    """

    session = await aiohttp_session.get_session(request)
    session.invalidate()
    return HTTPFound(location="/")


@routes.get("/login")
async def login(request: Request):
    """
    Redirect the user to the bot's Oauth login page.
    """

    return HTTPFound(location=vbu.web.get_discord_login_url(request, "/login_processor"))


@routes.post('/webhooks/minecraft_server_activity')
async def minecraft_server_activity(request:Request):
    """
    Handle Cerberus throwing data from the Minecraft server at us.
    """

    # Check the headers
    authorization = request.headers.get("Authorization", None)
    if authorization is None:
        return json_response(
            {
                "error": "No authorization token set.",
            },
            status=401,
        )

    # See if we got some POST data
    try:
        data = await request.json()
    except Exception as e:
        return json_response(
            {
                "error": f"Invalid JSON POST data set - {e}.",
            },
            status=400,
        )

    # See if we got a guild ID
    print(data)
    try:
        guild_id = int(data['discordGuild'])
    except KeyError:
        return json_response(
            {
                "error": "Missing discordGuild parameter from JSON data.",
            },
            status=400,
        )
    except ValueError:
        return json_response(
            {
                "error": "Provided discordGuild was not an integer.",
            },
            status=400,
        )

    # See if we got some players
    try:
        player_ids = [int(i) for i in data['onlineUsers']]
    except KeyError:
        return json_response(
            {
                "error": "Missing onlineUsers parameter from JSON data.",
            },
            status=400,
        )
    except ValueError:
        return json_response(
            {
                "error": "Provided onlineUsers was not an integer.",
            },
            status=400,
        )

    # See if there are any players online
    if not player_ids:
        return json_response(
            {
                "error": "",
                "message": "No users were passed - no data was added.",
            },
            status=204,
        )

    # See if their auth token was correct
    async with vbu.Database() as db:
        allowed_guild_rows = await db("SELECT * FROM guild_settings WHERE guild_id=$1", guild_id)
        if not allowed_guild_rows:
            return json_response(
                {
                    "error": "Provided guild ID does not match any given guild.",
                },
                status=401,
            )
        if allowed_guild_rows[0]['minecraft_srv_authorization'].strip() != authorization.strip():
            return json_response(
                {
                    "error": "Provided authorization token does not match the specified guild.",
                },
                status=401,
            )
        now = dt.utcnow()
        for uid in player_ids:
            await db(
                """
                INSERT INTO
                    user_points
                    (user_id, guild_id, timestamp, source)
                VALUES
                    ($1, $2, $3, 'minecraft')
                """,
                uid, guild_id, now,
            )
    return json_response(
        {
            "error": "",
            "message": "Added data successfully.",
        },
        status=201,
    )
