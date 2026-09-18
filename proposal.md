# Brain Waves: A Proposal for Intuitive Cabin Activity Scheduling Software

## High Level Goal
Create scheduling software that is *maintainable*, *stable*, and *well documented*. People other than myself should be able to understand and use the software in future years.

## Background
Camp Augusta is an overnight summer camp in California. I am the Puppet Master of camp augusta, which is a role that is in charge of scheduling. I am hoping to create a tool to help with one aspect of the schedule: cabin activities. Campers come for sessions, which are either one week or two weeks.

## Terminology
Cabin Activity (also called cabin acts): one hour during the standard summer camp day in which cabins do a unique activity of their choice with their counselor, often with other non-counselor staff support.
Village: Camp Augusta has four villages for different age-gender groups. There is a village for older/younger boys/girls. Pine is for younger boys, Cedar for older boys, Manzi for younger girls and Oak for older girls.
Village Leader (also called a VL): The person leading the counselors of a village and the person who is nominally in charge of cabin acts for the village.
VL Brain: The person determining which cabin activities run on which day.
Puppet Master: me, the person in charge of the daily staff schedule. The cabin act planning process is important to me because I used to be the VL Brain and because the cabin act schedule determines what schedule requests are needed for  non-counselor support staff.
HERO: a non-counselor support staff member

## The Current System
Village Leaders use Google Sheets. Each village leader first inputs the cabin activity options submitted by a cabin. The VL brain then organizes then decides which cabin acts to run and on which date. The VL Brain leaves comments on cabin activities that need more detail or they are concerned about. In these comments they mention other users who then respond to the comment to create conversation threads. The VL Brain switches the positions of two cabin acts by 1) selecting the cells of one cabin act block, 2) dragging those cells to blank cells somewhere else, 3) selecting the cells of another cabin act block, 4) dragging those cells to the position of the first cabin act, 5) selecting the cells of the first cabin act block, 6) dragging the first cabin act block to the original position of the second block.

See 

### Benefits
By using Google Sheets, all VLs can work on the cabin act schedule simultaneously. With the comment system, VLs, directors, and the Puppet Master can communicate information and hold virtual discussions threads.

### Pain Points
The simple and common task of reorganizing cabin acts is excessively tedious. With several people working at the same time and moving blocks around to empty cells, the sheet is prone to unwanted overlap and general chaos. Also, it would be nice if the state of the schedule requests for each day were organized and automatically updated.

## Solution
A program called "Brainwaves" will streamline the scheduling process by created a dedicated cross-platform desktop application for VLs to use.

## Design Details
The application GUI will be created with PySide and follow the same design aesthetic as Puppet Strings, the application made to support the Puppet Master. See @../puppet_strings/puppet_strings/app for details. The Interface should be professional, intuitive, and aesthetically pleasing.

## Details
- The app will be written in Python, connect to Google Sheets as the autoritative source of truth, and be distributed to Village Leaders as a single portable executable that can run on Windows, Mac, and Linux.
-  Cabin Acts are visually organized in cards. A card will look visually similar to the representation on Google Sheets. You can determine the best way to lay out a card. A card will include the following
	-  The title of the cabin act
	-  A brief description
	-  Materials needed (comma separated)
	-  Location (from a dropdown)
	-  Notes
	-  a checkbox of whether a van is needed
	-  A dropdown of the risk (with options "R", "G","Y", and "N")
	-  a check box of whether the armory is needed
	-  a check box of whether a picnic is needed
	-  a check box of whether non-picnic food is needed
	-  a list of "chips" at the bottom listing the HEROS needed. You can add a new staff member by clicking an addition button.
		-  The allowable values for the chips will come from the same staff list as in Puppet Strings. See @../puppet_strings/puppet_strings/sheets/skills.py for details on how staff are loaded. Assume that the user has access to the skills doc. I wouldn't want to write "staff.dylan", instead I would want to use the raw name in the skills doc, so "Dylan"

- The Google Sheets representation of the data will be very similar to the current, visually appealing card format. This will be the fundamental source of truth on the state of the schedule. The Brainwaves program will cache a version of the Google Sheets data to allow for a more responsive experience, and the program will very frequently update its cached state from Google Sheets.
- The app will have a toolbar with two buttons to change the stage of the workflow the user wants to switch to.
	1. Input stage: Village leaders input cabin activity data
		- They will input the data not in a boring form, but in an editable card format.
		- Each row of cards will be a different cabin. Different cabins can have different numbers of cards. Users can add a card with a plus button to the right of the row. The cards live in a sideways scrollable area.
			- Users can add a cabin within a village. Each cabin has a number and a counselor, with an optional co-counselor field
	2. Sorting Stage: the Brain shuffles around cabin acts while the other VLs make comments. A card can be quick-edited by double clicking on it.
		- Each row of cards will be cabins, grouped by villages. Each column will be days of the week, with an overflow zone tot he right of that.
		- Each day of the week can have an optional "sub-title". For instance, it's important to know at a glance that a Thursday might be Pizza Day
		- You will determine the best way to handle comments so that they are presented clearly and intuitively in a professional way.
		- Cabin acts can be shuffled only with another cabin act in the same row with a visual click-and-drag system. I leave it to you to make this feature clean and cool.
- Actually, I changed my mind. There will be no "two stage" system and it will be a single layout based on the "sorting stage" that fulfills all the functionality of the old two stage system.
 - The app will have a top toolbar to select the Session number and the week being edited.
- staff members should be able to comment directly through Google Sheets or through Brainwaves, depending on what they prefer.
-  I want you to create a Google Sheets template for going forward. The template will include blank cards with the updated information. It will keep a similar format to the current doc, but cleaned up and formatted in a way that you deem best.

## User experience
When opening the app for the first time, a screen will prompt the user for their Google Account credentials. This information is saved in persistent storage so they don't need to re-authenticate every time. The user will select the session and the week number they want. This information will be stored in persistent storage so that when they open the program it immediately goes back to the session and week they were previously editing. There will be a button in the top called "link to Google Sheets". This button will open up a navigator in which the user can browse their Google drive to select the folder with the cabin act session sheets. There will be one sheet for each week, with the name scheme being "Cabin Act Sorting - S2W1". There will be a button called Start New Week which will prompt the user for a session and a week, then create a new sheet based off the template. If a sheet with the same session and week already exists, the user will be notified and will not be able to create the new sheet.

The program will look for updates on startup and easily update on a single click if the user decides to.

## Documentation
Match the documentation system in Puppet Strings. See @../puppet_strings for a sense of how the documentation works.

## Existing Google Sheets
See the google sheet with ID 1boJSFEy0M8O5_E5txiLSwujRCK2kXW6a8lnTd9oEqxg for an example of the current workflow. Look especially at tab "CA - A" -- that's the only one that matters for our purposes.

## Code Style Requests
- Write self-documenting code. Of course you should explicitly document functions with comments, of course, but otherwise try to let the code "speak for itself." Where you do comment, keep the comments concise. Avoid superfluous adjectives, adverbs, or phrases in code, comments, or explanations that do not add essential technical information. Be direct.
- Operate from the philosophy that removing code is just as big of an improvement as adding a new feature. I want the code base to be concise.
- Write code that adheres to the idiomatic style, conventions, and official style guides of the target language. This includes formatting, naming, and general structure.
- Always prefer the "return early" pattern to reduce nesting and improve code flow legibility. Example: Instead of if (condition) { /* long block */ } else { return; }, use if (!condition) { return; } /* long block */.
- Avoid code duplication. Re-use code through functions, classes, helper utilities, or modules.
- If using external libraries, choose popular, well-maintained, and reputable ones appropriate for the task.
