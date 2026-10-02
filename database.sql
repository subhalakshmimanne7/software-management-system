PRAGMA foreign_keys = ON;

CREATE TABLE USERS (
  User_ID INTEGER PRIMARY KEY AUTOINCREMENT,
  Name TEXT NOT NULL,
  Email TEXT NOT NULL UNIQUE,
  Password_Hash TEXT NOT NULL
);

CREATE TABLE DEPARTMENT (
  Department_ID INTEGER PRIMARY KEY AUTOINCREMENT,
  Department_Name TEXT NOT NULL UNIQUE,
  Description TEXT,
  Location TEXT,
  Contact_Email TEXT
);

CREATE TABLE PROJECT (
  Project_ID INTEGER PRIMARY KEY AUTOINCREMENT,
  Project_Name TEXT NOT NULL,
  Description TEXT,
  Start_Date TEXT,
  End_Date TEXT,
  Project_Status TEXT NOT NULL DEFAULT 'In Progress',
  Department_ID INTEGER NOT NULL,
  FOREIGN KEY (Department_ID) REFERENCES DEPARTMENT(Department_ID) ON DELETE RESTRICT
);

CREATE TABLE DEVELOPER (
  Developer_ID INTEGER PRIMARY KEY AUTOINCREMENT,
  Developer_Name TEXT NOT NULL,
  Email TEXT NOT NULL UNIQUE
);

CREATE TABLE SOFTWARE (
  Software_ID INTEGER PRIMARY KEY AUTOINCREMENT,
  Software_Name TEXT NOT NULL,
  Description TEXT,
  Status TEXT NOT NULL DEFAULT 'Active',
  Project_ID INTEGER NOT NULL,
  FOREIGN KEY (Project_ID) REFERENCES PROJECT(Project_ID) ON DELETE RESTRICT
);

CREATE TABLE TECHNOLOGY (
  Technology_ID INTEGER PRIMARY KEY AUTOINCREMENT,
  Technology_Name TEXT NOT NULL,
  Technology_Type TEXT NOT NULL,
  Version TEXT,
  Description TEXT
);

-- M:N junction table
CREATE TABLE SOFTWARE_TECHNOLOGY (
  Software_ID INTEGER NOT NULL,
  Technology_ID INTEGER NOT NULL,
  PRIMARY KEY (Software_ID, Technology_ID),
  FOREIGN KEY (Software_ID) REFERENCES SOFTWARE(Software_ID) ON DELETE CASCADE,
  FOREIGN KEY (Technology_ID) REFERENCES TECHNOLOGY(Technology_ID) ON DELETE RESTRICT
);

CREATE TABLE VERSION (
  Version_ID INTEGER PRIMARY KEY AUTOINCREMENT,
  Software_ID INTEGER NOT NULL,
  Version_Number TEXT NOT NULL,
  Release_Date TEXT NOT NULL,
  FOREIGN KEY (Software_ID) REFERENCES SOFTWARE(Software_ID) ON DELETE CASCADE
);

CREATE TABLE LICENSE (
  License_ID INTEGER PRIMARY KEY AUTOINCREMENT,
  Software_ID INTEGER NOT NULL,
  License_Type TEXT NOT NULL,
  Start_Date TEXT NOT NULL,
  Expiry_Date TEXT NOT NULL,
  License_Status TEXT NOT NULL DEFAULT 'Active',
  FOREIGN KEY (Software_ID) REFERENCES SOFTWARE(Software_ID) ON DELETE CASCADE
);

CREATE TABLE BUG (
  Bug_ID INTEGER PRIMARY KEY AUTOINCREMENT,
  Software_ID INTEGER NOT NULL,
  Description TEXT NOT NULL,
  Severity TEXT NOT NULL CHECK (Severity IN ('Low','Medium','High','Critical')),
  Status TEXT NOT NULL CHECK (Status IN ('Open','In Progress','Resolved','Closed')),
  Reported_Date TEXT NOT NULL,
  FOREIGN KEY (Software_ID) REFERENCES SOFTWARE(Software_ID) ON DELETE CASCADE
);

CREATE TABLE MAINTENANCE (
  Maintenance_ID INTEGER PRIMARY KEY AUTOINCREMENT,
  Bug_ID INTEGER NOT NULL,
  Performed_By INTEGER NOT NULL,
  Maintenance_Date TEXT NOT NULL,
  Description TEXT NOT NULL,
  Status TEXT NOT NULL DEFAULT 'In Progress',
  FOREIGN KEY (Bug_ID) REFERENCES BUG(Bug_ID) ON DELETE CASCADE,
  FOREIGN KEY (Performed_By) REFERENCES DEVELOPER(Developer_ID) ON DELETE RESTRICT
);

-- ---------------------------- sample data ----------------------------
INSERT INTO DEPARTMENT VALUES
 (1,'Computer Science & Engineering','Core software development','Block A, Floor 2','cse@college.edu'),
 (2,'Information Technology','Campus infrastructure','Block B','it@college.edu'),
 (3,'Administration','Records and ERP','Main Office','admin@college.edu');

INSERT INTO PROJECT VALUES
 (1,'Campus ERP','Unified student and staff ERP',date('now','-200 day'),NULL,'In Progress',3),
 (2,'Library Suite','Catalog and lending',date('now','-400 day'),date('now','-30 day'),'Completed',2),
 (3,'Smart Attendance','Face-based attendance',date('now','-60 day'),NULL,'Planning',1),
 (4,'Exam Portal','Online exams',date('now','-150 day'),date('now','-20 day'),'In Progress',1);

INSERT INTO DEVELOPER VALUES
 (1,'Aditi Deshmukh','aditi@college.edu'),
 (2,'Rahul Verma','rahul@college.edu'),
 (3,'Sneha Rao','sneha@college.edu');

INSERT INTO TECHNOLOGY VALUES
 (1,'Python','Programming Language','3.11','General purpose language'),
 (2,'Flask','Web Framework','3.0','Python micro framework'),
 (3,'MySQL','Relational DB','8.0','SQL database'),
 (4,'React','Frontend Library','18','UI library'),
 (5,'Oracle','Relational DB','19c','Enterprise database');

INSERT INTO SOFTWARE VALUES
 (1,'Student Portal','Student-facing web portal','Active',1),
 (2,'Fee Manager','Fee collection','Testing',1),
 (3,'Library Catalog','Book search','Active',2),
 (4,'Attendance App','Mobile attendance','Development',3);

INSERT INTO SOFTWARE_TECHNOLOGY VALUES (1,1),(1,2),(1,3),(2,1),(2,5),(3,4),(3,3),(4,1),(4,4);

INSERT INTO VERSION VALUES
 (1,1,'v1.0.0',date('now','-180 day')),
 (2,1,'v1.1.0',date('now','-60 day')),
 (3,3,'v2.0.0',date('now','-120 day')),
 (4,2,'v0.9.0-rc',date('now','-20 day'));

INSERT INTO LICENSE VALUES
 (1,1,'MIT',date('now','-300 day'),date('now','+400 day'),'Active'),
 (2,2,'Commercial Enterprise',date('now','-500 day'),date('now','-15 day'),'Active'),
 (3,3,'Apache 2.0',date('now','-200 day'),date('now','+100 day'),'Active'),
 (4,4,'Trial',date('now','-40 day'),date('now','-10 day'),'Trial');

INSERT INTO BUG VALUES
 (1,1,'Login fails with special characters in password','Critical','Open',date('now','-5 day')),
 (2,2,'Receipt PDF shows wrong total','High','In Progress',date('now','-12 day')),
 (3,3,'Search is slow on large catalogs','Medium','Resolved',date('now','-40 day')),
 (4,1,'Typo on dashboard header','Low','Closed',date('now','-70 day')),
 (5,4,'Camera permission crash on Android','High','Open',date('now','-3 day'));

INSERT INTO MAINTENANCE VALUES
 (1,3,1,date('now','-30 day'),'Added index on title column','Completed'),
 (2,2,2,date('now','-8 day'),'Rewriting total calculation','In Progress'),
 (3,4,3,date('now','-60 day'),'Fixed header text','Completed');
