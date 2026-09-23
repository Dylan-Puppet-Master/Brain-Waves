# Brain Waves

Brain Waves is a software tool to help Village Leaders plan Cabin Activities. It is essentially an alternate frontend to Google Sheets with various quality-of-life improvements added in. Village Leaders are free to continue using Google Sheets if they want -- all the information (including comments) will update in almost-real-time within Brain Waves.

The creation of Brain Waves was motivated by a wish and a wonder.

**The wish** for the ability to simply drag, drop, and swap cabin acts across the week. The current system of sorting cabin acts is, in my opinion, unnecessarilly tedious and not what Google Sheets was designed for.

**The wonder** of how possible it would be to consolidate all staff scheduling -- including HERO scheduling -- under one Puppet Master system. With progress being made towards automating the staff schedule (see [Puppet Strings](https://github.com/Dylan-Puppet-Master/Puppet-Strings)), it would be extremely convenient for cabin activity staffing requests to be in a standardized format.

**Surprise!** Brain Waves solves both of these problems and then some, with the only techincal drawback being slightly higher latencies in real-time collaboration. 

![The board](img/app.png)


## Where things live

| Thing | Where |
|---|---|
| One week of cabin acts | A Google spreadsheet named `Cabin Act Sorting - S2W1` |
| Every week of a summer | One Google Drive folder, which you pick once |
| Staff names for the HERO chips | The Skills doc, the same one Puppet Strings reads |
| Your sign-in, folder and week | Your own computer, so the program opens where you left it |
| The code | This repository, one Python package |

Start with [Install and set up](install.md).
