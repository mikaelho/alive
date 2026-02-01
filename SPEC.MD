SPEC
====

Goal: Automatically updating web app for several users. All components should update for all users as they are changed bu one user.

Tech stack: Python with PyView, later adding Django.

Concepts:
- Component: reusable, can represent individual data fields and similar

Steps:
- First component: text field that is in display mode until tapped, then editable in markdown
- Simple page that has just a text field with a simple backing state
- Edit/display state per client
- Same page accessible by several clients
- Updates by one client update others
- Support text area, similarly
- Card that uses text field as a title and area for content
- List of cards that has a state of list of dicts, dicts have ”title” and ”content”
- State is shared for several clients
- List supports changing the order