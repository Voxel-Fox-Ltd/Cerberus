# Cerberus

Cerberus is a small-time activity bot that handles roles based on _weekly_ activity rather than _all-time_ activity. This means that users gain and lose activity roles over time, instead of the common activity bots you get now where people can be active for one week 7 months ago and now they're just hangin' out with the highest activity role.

## Where do points come from?

Much like other levelling bots, Cerberus counts one message every minute. Each counted message gives you one point (seen with the `'points` command), which goes to your weekly max. _Unlike_ most other levelling bots, Cerberus also tracks VC activity, giving a user 1/5th of a point for every minute they're in a VC (assuming they're unmuted, undeafened, not alone, and not in an AFK channel).

Points are calculated as an N-day rolling sum, so if you're especially active on one Monday, that won't stand forever. Those points will all go away.

## How many points do I have?

Because of the inherent nature of constantly gaining and losing points, Cerberus wouldn't work well with a "levels" system. What it _does_ show you, however, is your weekly activity over time.

Cerberus has the `'graph` command, which lets you see your weekly activity.

![](https://voxelfox.co.uk/static/images/cerberus/7-day-graph.png)

For this particular graph, each point on the graph is the sum of the user's activity on that particular day, and the colours in the background are the colours of the role the user achieves at that level of acitivity.

You can also see your activity over a _larger_ period of time if you really want to.

![](https://voxelfox.co.uk/static/images/cerberus/180-day-graph.png)

## How do I use it?

There's only a few commands that are important to Cerberus, but after that it's just plug and play.

* `'setup`
    * Takes you through setting up the bot. Here you can set whether users lose old roles on ranking up, which roles users can gain, and channels/roles that are blacklisted from gaining points.
* `'points @User`
    * Shows you how many points the given user has gotten.
* `'graph @User`
    * Shows you the activity graph of a given user.
* `'roles`
    * Shows you which roles you'll get at each level of activity.
* `'prefix new_prefix`
    * Apostrophe not good enough for you? You can change it with the prefix command. If you manage to _forget_ your prefix, you can always ping the bot (eg `@Cerberus prefix '` will reset the prefix back to an apostrophe).
