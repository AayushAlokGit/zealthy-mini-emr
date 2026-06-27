Zealthy - Full Stack Engineering Exercise

This exercise is designed to screen for technical soundness and also better understand
management philosophy. Note that we recognize that all candidates will be able to complete the
coding exercise, but we are looking for style and quality of code.

You should attempt to complete this in less than 5 hours of dedicated time and submit the completed exercise as both a github repo URL, and a live deployed demo URL to Ellah (ellah.escasa@getzealthy.com) and Shanti (shantibraford@gmail.com). You may complete this in one or more sittings, and should do so within a week of receiving the exercise prompt.


The coding exercise is to create a mini-EMR and Patient Portal application. Providers would like to be able to manage patients via the mini-EMR, such as scheduling appointments and prescribing medications. Patients should be able to view their upcoming appointments and medication refills, etc. The app should be broken down into the two sections outlined below. Example JSON data is provided below, but a database should be employed such that new entries can be added, and existing ones modified.

Section 1 - The “mini” EMR

This is to be an admin interface with just a small fraction of the features normally found on an EMR application. The EMR should reside at the url path “/admin” and should not require authentication (normally it would, of course). The main page should be a table of users in the system. Some at-a-glance data should be visible on this table. Admins should then be able to drill down into a patient record and view their upcoming appointments and list of prescribed medications. Sample data for these is included as JSON below.

Some requirements of the mini-EMR:
* Patient prescriptions can be managed (CRUD)
* Patient appointments can be managed (CRUD)
* Patient data can be managed (CRU) - so a New patient form needs to allow creation as well

Section 2 - The Patient Portal

A way for patients to view their info such as upcoming appointments and medication refills. The Patient Portal should reside at the root “/“ path of the application. A login form should be displayed with email and password fields for the patient to login. One should be able to login with the sample credentials provided, or with credentials entered when creating new users via the EMR.

The main page of the Patient Portal should provide the patient with a summary of the most important data—any appointments within the next 7 days, any medications with refills scheduled in the next 7 days, and basic patient info.

Some requirements of the Patient Portal:
* Patients should be able to drill down and see their full upcoming appointment schedule
* Patients should be able to drill down and see info about all of their prescriptions

Please submit your completed exercise URLs for both the github repository as well as a deployed application somewhere (Vercel, Netlify, Heroku, AWS, etc) to Ellah (ellah.escasa@getzealthy.com).

JSON data to seed your application can be found at:
https://gist.github.com/sbraford/73f63d75bb995b6597754c1707e40cc2

Frequently Asked Questions

Which programming languages / frameworks can I use?

Please use React or NextJS for the frontend of the application. The backend can be written in any language/framework of your choosing–including but not limited to Node, NextJS, python, Ruby on Rails, Java, etc.

What are some of the requirements of the mini-EMR?

Please use the data.json file provided via the link above to seed your database with the possible medications and dosages that can be prescribed to a patient. The patient prescription form should include the same data from the JSON file: medication name, dosage, quantity, refill date and refill schedule (i.e. monthly).

The patient appointment form should work similarly as per the sample included appointments, including a provider name, date time of the first appointment and a repeat schedule. Please provide a way to end recurring appointments, and to schedule new appointments. The provider name field can be a free-form text entry field.

For patient creation, please allow setting of the patient password. (One normally wouldn't code it that way but it will help us in testing the app)

What are some of the requirements of the Patient Portal?

Upon logging in via the main root page of the app ("/"), the user should be taken to their patient portal. The main page should just consist of a summary of the most important patient data and upcoming appointments/refills. The user should have a way to drill down into appointments, and medications, and see the full upcoming schedule of each (going out up to 3 months from the current date).

What platform should I deploy my application to as a demo?

You can choose any platform(s) of your choosing. Vercel, Netlify, Heroku, fly.io, AWS, Azure, etc. are all perfectly fine.


