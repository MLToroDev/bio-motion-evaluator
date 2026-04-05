

Journal of Informatics and Web Engineering
https://doi.org/10.33093/jiwe.2026.5.1.15
## © Universiti Telekom Sdn Bhd.
Published by MMU Press. URL: https://journals.mmupress.com/jiwe

Journal of Informatics and
## Web Engineering
Vol. 5 No. 1 (February 2026) eISSN: 2821-370X
Real-Time Posture Monitoring for Effective
Exercise Using MediaPipe Python

Wan Izzul Wafiq bin Wan Noor Asmawi
## 1
and S. Prabha Kumaresan
## 2*

## 1,2
Faculty of Computing and Informatics, Multimedia University, Persiaran Multimedia, 63100 Cyberjaya, Malaysia.
## 2
Center of Natural Language Processing, CoE for Artificial Intelligence, Multimedia University, Persiaran Multimedia, 63100
## Cyberjaya, Malaysia.
*Corresponding author: (prabha.kumaresan@mmu.edu.my; ORCiD: 0000-0002-0969-7428)

Abstract - Maintaining proper posture during exercise is crucial for preventing injuries and maximizing workout efficiency. This
project aims to develop a real-time posture monitoring system using MediaPipe and OpenCV to provide instant feedback on the
exercise  form.  The  system  captures  video  input through  a  webcam,  processes  it  using  OpenCV,  and utilizes MediaPipe’s pose-
estimation model to detect key body landmarks. By analysing the joint angles and comparing them to predefined optimal postures,
the system evaluates the user’s form and provides corrective feedback in real time. This approach eliminates the need for expensive
wearable sensors, making posture monitoring more accessible and user friendly. The literature review highlights the effectiveness
of  computer  vision-based  solutions  in  fitness  applications  and  identifies  key  challenges,  such  as  occlusions,  varying  lighting
conditions, and real-time processing constraints. The proposed system addresses these issues by optimizing the pose-estimation
accuracy and feedback mechanisms. Testing and user surveys confirmed the system’s effectiveness, achieving 90% accuracy for
squat posture detection and 86% accuracy for lunges under typical home-workout conditions. The expected outcome of this project
is a functional real-time exercise posture monitoring system that enhances the user training experience by ensuring a proper form.
Future improvements may involve integrating machine learning techniques to personalize feedback and expand the system to multi-
user  environments.  This  project  contributes  to  the  advancement  of  computer  vision  applications  in  fitness  and  rehabilitation
domains.
Keywords— MediaPipe, OpenCV, Real-time Posture Monitoring, Joint Angle Calculation, Squats, Lunges

## Received: 7 June 2025; Accepted: 7 August 2025; Published: 16 February 2026
This is an open access article under the CC BY-NC-ND 4.0 license.

## 1. INTRODUCTION
Home workouts have become increasingly popular nowadays, specifically after the world shift to remote and stay-
at-home  lifestyles,  which  have  brought their own  challenges  and  advantages.  Performing  exercise  alone  at  home
without professional supervision can lead to ineffective workout efficiency, incorrect posture, and high risk of injury.
The lack of real-time feedback during unsupervised workouts may result in incorrect movements, which can hinder

Journal of Informatics and Web Engineering                Vol. 5 No.1 (February 2026)
## 237

exercise  progress  or  cause  long-term  harm.  These  issues  are  especially  significant  for  rehabilitation  patients  or
individuals  recovering  from  injuries,  such  as knee  surgery  patients,  who  need  to  follow  proper  forms  to  avoid
setbacks.  The  motivation  for this  project  stemmed  from  a  personal  rehabilitation  experience  of  Anterior  Cruciate
Ligament  (ACL)  injury,  where  the  absence  of  real-time  posture  guidance  during  physiotherapy  exercises  made
recovery more challenging and worrying. Recognizing this gap, this project aims to create an accessible, low-cost,
and user-friendly solution that helps users correct their exercise posture in real time without requiring guidance from
professional trainers or expensive equipment.
Existing  posture  correction  systems  require  expensive  equipment  and  are  complex  to  set  up,  making  them
inaccessible to anyone who needs them. These concerns can be addressed with the development of this project, which
is a real-time posture monitoring system that relies only on a standard webcam that will make it low-cost, accessible,
and user-friendly. This project uses MediaPipe Pose to detect 33 key body landmarks and angles and OpenCV for
live frame input and instant feedback. The system only focuses on two types of exercises, squats and lunges, which
are  commonly  performed  by rehabilitation  patients  recovering  from  knee  surgery  that  require  proper posture  and
form to be free from any injury and earn an effective workout session. By leveraging computer vision and Python’s
MediaPipe Pose estimation, the system provides live posture monitoring with color-coded feedback to guide the user
to fix their posture in real time to ensure a proper form.
The  objective  of  this  project  was  to  develop  a  reliable  posture  detection  system  that  operates  in  real  time  by
leveraging MediaPipe Pose Estimation and OpenCV, relying only on a standard webcam. It is designed to assess and
categorize posture accuracy based on key body angles during squats and lunges, classify the posture as good, adjust,
or bad, and offer immediate on-screen color-coded feedback to help users maintain a proper form. In addition, the
system  includes  a  simple  graphical  user  interface  (GUI)  built  with  Tkinter  to  improve  its  usability.  Through  this
approach, the project contributes to the growing use of computer vision in fitness and rehabilitation by offering an
intelligent real-time solution that ensures safe and effective exercise practices. This project has great potential to be
advantageous  for  a  wide  range  of  users, such  as individuals  who  exercise  independently  at  home,  including
beginners, workout enthusiasts, and rehabilitation patients.

## 2. LITERATURE REVIEW
The  growth  of  computer  vision  and  human  pose  estimation  technologies  has  recently  attracted  attention.  Manual
poster  correction  relies  on  manual  observations  from  professional  trainers  or  physical  therapist  trainers  that  the
correctness of the exercise form is not fully accurate at all times. The development of a posture monitoring system
will help workout enthusiasts and deliver a cost-effective system that will improve the effectiveness of exercise [1].
There  are  several  types  of  pose-estimation  frameworks,  such  as MediaPipe,  TensorFlow,  and OpenPose.  These
frameworks utilize modern solution technologies, such as deep learning and machine learning [2]. This section on
literature review discusses and analyses existing work related to posture monitoring. This research aims to discover
the strengths, limitations, and future enhancements of other projects to improve and achieve high accuracy in form
correction [3].

2.1 Categorization by Methods and Techniques Used
Based on this research paper, many of its studies leverage MediaPipe Pose as their main framework. [4] achieved
78% Jaccard Similarity with human evaluators on the standardized pulling posture of air cadets using MediaPipe and
OpenCV  by  applying  form  checking.  Similarly, [5] offers  a  real-time  posture  monitoring  system  with  landmark
detection and algorithm-based posture analysis. Moreover, exercises such as crunches,  squats, and push-ups were
analysed by  the  development of a  Personal  Exercise  Trainer from [6],  which  uses  pose  estimation  to  track  each
exercise  movement. The Exponential  Moving  Average  (EMA)  was  applied  in [7] to  achieve  stable  landmark
coordination and improve the accuracy of squat training assistance by incorporating dynamic thresholding techniques
for motion state classification. A high accuracy in evaluating exercises by employing calculation of joint angle, pull-
ups (92%), push-ups (83%), and squats (78%) shows the effectiveness of pose estimation for pose correction [8].
Machine  learning  has  also been  applied  using  Random  Forest classifiers  for pose  classification.  For  example,  a
system was designed to analyse key point movements to aid Parkinson’s disease patients while performing specific
physiotherapy exercises, utilizing Random Forest, achieving an accuracy of 97.13% for fingertip exercises and 98.26%
for claw stretch exercises [9]. Correspondingly, another study also leveraged Random Forest classification, but on

Journal of Informatics and Web Engineering                Vol. 5 No.1 (February 2026)
## 238

sports posture analysis. Their results showed an accuracy of 85.03% in predicting crickets, football, and basketball
## [10].

2.2 Accuracy and Performance
In addition, a system was developed that primarily focused on detecting real-time posture tracking and a workout
repetition counter by leveraging MediaPipe and OpenCV to analyse posture alignment and provide instant feedback
[11,  [12].  Some  research  introduced  motion  tracking  systems  for  real-time  movement  analysis  using  joint  angle
calculations via trigonometry but lacked advanced classification techniques [13], [14]. Moreover, [15] incorporated
deep learning model classification, and the Bi-GRU model that acquires a 94% accuracy rate with an attention layer
to classify squats surpasses other models,  Bi-LSTM and Bi-RNN  alternative, owing to its superiority in handling
temporal dependencies. [16] employed machine learning classifiers such as KNN, Random Forest to track improper
lifting techniques in a workplace setting, with Random Forest management to record the highest accuracy of 99.71%.
Some studies have  incorporated  machine-learning  models  to  improve  the  performance  of  posture  detection  and
classification on a real-time tracking base. By utilizing the COCO 2020 dataset and an exercise-specific algorithm
for each posture, it achieved an accuracy rate of 87 % %for correct repetition [17-18]. A study that implemented the
most advanced Artificial Intelligence (AI) was from [19], who developed AI-FIT COACH,  which is an AI-based
mobile application that integrates pose detection correction and smart guidance. The program leveraged TensorFlow
and MediaPipe for real-time posture monitoring and applied voice assistance and video uploads for delayed analysis.
Lastly, CNN-GRU models applied to yoga posture correction for temporal spatial analysis of 24 yoga poses managed
to record an impressive 98.17% training accuracy and 93.28% test accuracy [20].

## 3. RESEARCH METHODOLOGY
The methodology for this posture monitoring project aims to achieve high accuracy along with a correct and proper
posture for performing squats and lunges by leveraging MediaPipe Python. Live video frames on standard webcams,
pose  detection  of  body  landmarks,  key  joint  angle  calculations,  and  instant  correction  feedback  were  the  main
purposes of this project. The process was built on three main structures: posture detection, key joint angle analysis,
real-time feedback integration, and proper testing and validation.
First, video input is captured live using a webcam and will continue to be processed by the OpenCV implementation.
33  key  body  landmarks  were  extracted  by  MediaPipe  for  each  captured  frame.  Important  data  are  collected  by
enabling the detailed tracking of user movements and are vital for the calculation of joint angles. Critical joint angles,
such as the hip, knee, and ankle, were evaluated based on threshold recommendations from the professional. With
this,  the  system  should  be  able  to  assess  whether  the  exercise  performed  is  correct  or  incorrect  to  maintain
effectiveness and avoid unnecessary injury.
The next phase is related to interactions between the system and user. Color-coded feedback provides guidance to
the user as a real-time feedback mechanism to adjust posture while performing an exercise. As the session continues,
the user’s form will be evaluated by providing the necessary feedback to retain an efficient exercise session. The
final system section includes the involvement of multiple users to assess the accuracy of the pose detection. A survey
was  conducted  to  test  the  usability  and  adaptability  of  this  system  in  real-world  home  workouts  in  various
environments such as lighting conditions, clothing, and different types of users. The feedback responses collected
help to improve the system and prove its effectiveness on real users. Figure 1 illustrates the workflow of the system,
which starts by capturing real-time video feed from a webcam and then processing it using OpenCV.
Body landmarks of the posture that are detected with MediaPipe Pose are analysed by the system by calculating the
key joint angles that are involved in each exercise. These calculations help determine whether the user is performing
the correct posture while performing exercises on squats or lunges.
Once the angle was calculated, the system assessed whether the exercise session was ongoing. If it remains active,
the system will continue to show the results of the exercise evaluation based on the threshold set. Green indicators
are displayed on the screen as a correct posture performed, while red indicator, “Bad Posture” as to let the user know
they need to adjust their body form. This real-time correction feedback helps the user make real-time adjustments to

Journal of Informatics and Web Engineering                Vol. 5 No.1 (February 2026)
## 239

their posture. The loop continues if the session is still active, allowing the system to steadily monitor user posture
and display immediate feedback correction.


## Figure 1. Activity Diagram

As shown in Figure 2, the MediaPipe Pose model detects 33 key body landmarks that are used for full-body posture
tracking.



Figure 2. MediaPipe Pose Landmarks

These landmarks represent critical joints and points such as the nose, eyes, shoulders, elbows, wrists, hips, knees,
ankles,  and  toes.  By  accurately  identifying  these  points  in  real-time  from  a  video  frame,  MediaPipe  enables  the
system to track the user's posture and movement. In this project, these landmarks are essential for calculating joint

Journal of Informatics and Web Engineering                Vol. 5 No.1 (February 2026)
## 240

angles, especially at the hips, knees, and ankles (landmarks 23–28), to determine whether exercising on squats or
lunges is performed correctly. The landmark-based structure ensures precision, making it a powerful tool for posture
analysis and feedback generation during physical exercises. Figure 3 shows the angle calculation formula.


## Figure 3. Angle Calculation Formula
The calculate_angle function  is  the  core  part  of  the  real-time  posture  monitoring  system  and  is  responsible  for
determining the exact angle formed by the MediaPie Pose on three key body points, namely the hip, knee, and ankle.
When the system captures video frames through the webcam, it identifies these landmarks as coordinate pairs of the
detection joint angle and passes them to this function. Inside the function, each point was converted into a NumPy
array to make it easier to achieve efficient mathematical operations. Using basic trigonometry, the function calculates
the angle between the vectors extending from the middle point (knee) to the other two points (hip and ankle). This
is performed with the arctan2 function, which computes the difference in orientation between the two vectors and
converts the result from radians to degrees. The function ensures that the returned angle stays within a valid range
by adjusting any value above 180 °to its equivalent interior angle because joint bend measurements are meaningful
only within 0 °to 180 °. By returning this precise angle, the system can instantly evaluate whether a squat or lunge
is performed within the safe and effective thresholds. This allows the application to provide clear, real-time feedback,
classifying each repetition as good, requiring adjustment, or incorrect, thereby guiding the user toward proper form
and helping to prevent injury.
The proposed system uses MediaPipe’s pose estimation landmarks to assess posture accuracy in real time, focusing
specifically  on  key  lower-body  joints,  the  hips  (landmarks  23  and  24),  knees  (landmarks  25  and  26),  and  ankles
(landmarks 27 and 28). For squats, as illustrated in Figure 4, both legs were monitored symmetrically, and a good
squat  was  defined  as  a  knee  angle  (hip-knee-ankle)  within  the  range  of  80°  to 100°.  This  ensures  that  the  user  is
squatting deep enough to activate major muscle groups such as the quadriceps, glutes, and hamstrings, without going
deep enough to cause joint strain. Angles below 80° may indicate over-flexion and risk of injury, whereas angles
above 100° suggest an incomplete squat with reduced training effectiveness.


## Figure 4. Squat Angle
In the case of lunges, as shown in Figure 5, the system analyses each leg independently owing to the staggered stance.
A good lunge posture requires that the front and back legs maintain joint angles between 90° and 130°, measured

Journal of Informatics and Web Engineering                Vol. 5 No.1 (February 2026)
## 241

again using the same hip-knee-ankle landmarks (23–28). For the front leg, this angle helped confirm that the thigh
was  parallel  to  the  ground  and  the  knee  remained  aligned  over  the  ankle,  whereas  for  the  back  leg,  it  ensured
appropriate stretch and stability without overloading the knee joint. Angles outside this range may suggest improper
foot placement, shallow depth, or a potential imbalance. By constantly comparing the measured angles to the defined
optimal  ranges,  the  system  offers  immediate  visual  feedback to guide the user’s adjustments and support correct
posture  and  movement  over  time,  making  it  an  effective  aid  for  both  general  fitness  routines  and  physiotherapy
rehabilitation exercises.

## Figure 5. Lunges Angle

## 4. SYSTEM REQUIREMENTS AND TESTING
The  testing phase of Real-Time  Posture  Monitoring for Effective  Exercise using the MediaPipe  Python system is
described here. It presents evidence of how the system was verified in terms of usability, detection accuracy, real-
time performance, and practical effectiveness under different conditions.
## 4.1 System Limitations
- 2D Pose Detection
The system relies on 2D pose estimation via standard webcams, which lack the depth perception of 3D
systems. This limits the accuracy of the tracking of complex or nuanced movements.

## • Environmental Factors
is affected by poor lighting, cluttered backgrounds, and unstable camera angles, which can reduce the
precision of postural detection in uncontrolled settings.

## • User Variability
Differences in body types, clothing, or exercise styles may hinder the consistent detection of key
landmarks, particularly when joints are obscured by loose or dark clothing.

## • Exercise Scope
The system currently supports only a limited range of bodyweight exercises, involving only squats and
lunges. It does not accommodate exercises involving equipment or highly dynamic movements, which
would require a more complex calibration.

## • Basic Feedback Mechanism
is focused solely on posture correction. The system does not provide advanced features, such as workout
tracking, training progression, or personalized recommendations.

- Single-User Design
The system supports only one user at a time and cannot distinguish between multiple users in the same
camera frame, making it unsuitable for group workouts.

## • Webcam Dependency
Accuracy  is  heavily  reliant  on the  webcam  quality.  Low-resolution  or  low-framerate  webcams  may
significantly degrade the detection performance.


Journal of Informatics and Web Engineering                Vol. 5 No.1 (February 2026)
## 242

4.2 System User Interface (GUI)
Below is  the  main  GUI  page  of  the system (Figure  6), which  was  developed  using Tkinter. The  GUI  provides  a
simple Start and Quit button, displays the selected mode (Squat or Lunge), and shows real-time feedback during the
exercise.


Figure 6. Main GUI
## Description:
- The GUI is designed to be lightweight and easy to navigate.
- Green button for Start and Red button for quit.
- Users are given guidance and switch modes by pressing S (Squat) or L (Lunge), and for stopping the program,
Q (Quit program).

4.3 System Requirements and User Positioning
Before starting any exercise session with the Real-Time Posture Monitoring System, it is important to follow the basic
setup requirements to ensure that the system correctly detects all body landmarks and provides accurate feedback.
a. Full-Body Visibility
The user must position themselves such that their entire body, from head to toe, is fully visible in the camera
frame, as shown in Figure 7. This ensures that the MediaPipe Pose can track all 33 key landmarks, including
the hips, knees, and ankles, which are essential for calculating joint angles.
b. Distance from Camera:
Users were required to stand approximately 2 meters (±0.5 meters) away from the camera. This distance is
optimal for capturing the full body, while maintaining sufficient detail for precise pose detection.
c. Environment Setup:
The testing area should have sufficient lighting and a clear, uncluttered background to reduce the detection
errors caused by shadows, obstacles, or background noise.
## Description:
- Before starting, position yourself, so your whole body (head-to-toe) is visible on the screen.
- This helps the system detect all body landmarks correctly.
- Full visibility ensures accurate joint angle calculation and posture classification.
- Proper framing allows the system to give reliable feedback for squats and lunges.


Journal of Informatics and Web Engineering                Vol. 5 No.1 (February 2026)
## 243


Figure 7. Example Proper Full-Body Visibility

## 5. RESULTS AND DISCUSSIONS
## 5.1 Functional Testing
Table 1 shows the functional testing of the test case with its expected output.
## Table 1.  Functional Testing
## Test Case Description Expected Output Result
Webcam Activation Start webcam on clicking the
“Start” button in GUI
Webcam feed starts and appears
on screen
## Pass
Pose Detection Detect 33 body landmarks using
MediaPipe
Landmarks correctly shown on
user’s body in real time
## Pass
Joint Angle Calculation Calculate knee, hip, and ankle
angles using landmark
coordinates
Accurate angle values computed
in degrees
## Pass
Exercise Classification Categorize squat/lunge as Good,
Adjust, or Bad based on angle
thresholds
Correct feedback label appears:
## Good / Adjust / Bad
## Pass
Mode Switching Switch between squat and lunge
modes using keys ('S' for squat,
'L' for lunge)
Mode changes and detects
correct exercise type
## Pass
Live Feedback Display Provide visual feedback on
posture in real time
Coloured label displayed
(green/yellow/red) with angle
info
## Pass
Repetition Counter Count number of valid repetitions
(squats or lunges)
Repetition count increases only
when posture is correct
## Pass
Data Logging Log results to a text file after
session
File with session summary saved
(FPS, total squats, lunges)
## Pass
GUI Start/Quit Button Ensure Start activates camera,
and Quit exits the program
Application responds correctly to
both buttons
## Pass
## User Instructions
## Display
Show mode-switch and quit
instructions on GUI
Instructions visible and readable
to users
## Pass

5.2 User Testing and Survey Results
A survey on user testing and feedback was conducted with 30 respondents (Figure 8). This survey aims to collect
practical data by assessing system performance on the accuracy of each squat and lunge performed under different
conditions and environments, and to explore user feedback on how the system operates.

Journal of Informatics and Web Engineering                Vol. 5 No.1 (February 2026)
## 244



Figure 8. Survey Respondents count
Figure 9 illustrates the variation in participants’ height and weight, with the tallest measuring 190 cm and the shortest
163 cm. The heaviest respondent weighed 100 kg, whereas the lightest weighed 46 kg. Fitness levels were distributed
in 46.7% of beginners, 33.3% of intermediate athletes, and 20% of athletes.


Figure 9. Survey (Height, Weight & Fitness Level) Distribution

The  age  of  respondents  is  illustrated  in  Figure  10,  ranging  from  18  to  26  years,  with  the  youngest
participant being 18 and the oldest being 26.
The  results  in Figures  11 (Squat  accuracy) and 12 (Lunges  accuracy)  show  that  the  developed  system
effectively identifies correct and incorrect postures with a high level of accuracy.



Journal of Informatics and Web Engineering                Vol. 5 No.1 (February 2026)
## 245

## .
## Figure 10. Survey Age Distribution

## Figure 11. Squat Accuracy


## Figure 12. Lunges Accuracy


Journal of Informatics and Web Engineering                Vol. 5 No.1 (February 2026)
## 246

On average, out of five repetitions for each user, the system achieved 90% accuracy in detecting the correct squat
posture and 86% accuracy in detecting the proper lunge posture. Lighting conditions also play a major role in how
well the system performs, and bright lighting shows a high accuracy in detecting the correct posture. Users’ clothing
also affects system detection, and it is recommended to wear a standard fit or sportwear while performing the exercise
while  using  the  system.  These  performance  levels  make  the  system  suitable  for  everyday  use,  even  for  standard
consumer laptops.

## 5.3 Sample Output Images
In the squat output (Table  2), the  system displays a  clear visualization of the  user’s posture  with body landmarks
highlighted  on  the  screen,  showing  the  alignment  of  the  hips,  knees,  and  ankles.  The  system  uses  a  color-coded
feedback system, with green indicating the correct squatting position. The angle between the thigh and calf (measured
at  the  knee) is likely to be shown as a numerical  value, with the system confirming that the  user has achieved an
optimal angle between 80° and 100°. The screen also likely provides real-time feedback such as “Good Squat” in
green text to reassure the user that their posture is correct, encouraging continued proper form. If the angle is outside
the correct range, the system might highlight the posture in yellow or red, offering corrective suggestions like “Adjust
## Squat”.
## Table 2. Squat Output
## Sample Squats Output Description



## Good Squat

- Green body landmarks.
- Knee angle is within the
ideal range (80°–100°).




## Adjust Squat

- Yellow body landmarks.
- Knee angle is slightly
outside the ideal range
(60°–79° or 101°–120°)

Journal of Informatics and Web Engineering                Vol. 5 No.1 (February 2026)
## 247




## Bad Squat

- Red body landmarks.
- Knee angle is not in the
target range (<60° or
## >120°).


For lunges, as shown in Table 3, the output displays similar landmark tracking, with a focus on both the front and
back legs. The front leg angle (between the hip, knee, and ankle) and the back leg angle were calculated and displayed
on the screen. When both angles fall within the predefined optimal range (e.g., the front leg between 90° and 130°
and the back leg between 90° and 190°), the system displays a green message, such as “Good Lunge.” Color-coded
feedback visually helps the user identify when they are performing the lunge correctly. If the angles deviate from the
ideal range, the system provides corrective feedback indicating areas for adjustment to achieve a better form. Real-
time feedback enables users to make immediate adjustments, thereby improving their performance over time.
## Table 3. Lunges Output
## Sample Lunges Output Description




## Good Lunges

- Green body landmarks.
- The user’s front leg is bent
at 90°–130°, and the back
leg is extended at 90°–190°.



## Adjust Lunges

- Yellow body landmarks.
- One or both leg angles are
slightly outside the target
range.

Journal of Informatics and Web Engineering                Vol. 5 No.1 (February 2026)
## 248



## Bad Lunges

- Red body landmarks.
- Posture is significantly
misaligned not in the target
range.

The solution offered by this system has significant advantages over manual or traditional postural correction. A high-
end system may offer slightly more accurate measurements, but it also relies on expensive hardware and a complex
setup. However, this standard webcam still provides acceptable effectiveness, affordability, and functionality. The
use  of  MediaPipe  ensures  efficient  processing,  which  requires  a  standard  computational  method  that  allows  this
system to be widely used by anyone.

## 6. CONCLUSION
This project successfully developed and tested an AI-powered real-time posture monitoring system using MediaPipe
and OpenCV, to enhance the safety and effectiveness of home workouts. By focusing on two fundamental exercises,
squats, and lunges, the system demonstrates how computer vision can be used to assess posture accuracy, provide
immediate  feedback,  and  assist  users  in  performing  exercises  in  the  proper  form.  The  use  of  a  standard  webcam
makes  the  system  highly  accessible  and  cost-effective,  lowering  barriers  to  entry  for  fitness  enthusiasts  and
rehabilitation patients. Throughout the development, the system architecture was structured around four main phases:
data  collection,  posture  detection  and  analysis,  feedback  generation,  and  system  validation.  The  integration  of
MediaPipe  for  landmark  detection  and  custom  logic  for  joint  angle  calculations  allows  the  system  to  evaluate
movement with high precision. Visual feedback mechanisms and color-coded indicators give users real-time cues to
correct their form during active workouts. Compared with traditional motion-capture systems, this solution offers a
balance of affordability, portability, and performance. Its simplicity in setup, requiring only a webcam and standard
hardware,  makes  it  a  practical  tool  for  home  use.  The  adoption  of  open-source  libraries  ensures  flexibility  and
scalability for future improvements or customizations tailored to individual user needs and specific training goals.
In future work, the system can be expanded to support a wider variety of exercises, such as push-ups, planks, or yoga
poses,  increasing  its  versatility  for  both  fitness  and  rehabilitation.  Machine-learning  techniques  can  also  be
introduced to improve the adaptability of posture classification and recommendations over time. These advancements
would extend the value of the system as a long-term fitness companion and contribute significantly to the evolving
field of AI-driven health technologies.

## ACKNOWLEDGEMENT
The authors received no funding from any party for the research and publication of this article.

## FUNDING STATEMENT
The authors received no funding from any party for the research and publication of this article.




Journal of Informatics and Web Engineering                Vol. 5 No.1 (February 2026)
## 249

## AUTHOR CONTRIBUTIONS
Wan  Izzul  Wafiq  bin  Wan  Noor  Asmawi:  Conceptualization,  Data  Curation,  Methodology,  Validation,  Writing –
## Original Draft Preparation;
S. Prabha Kumaresan: Conceptualization, Project Administration, Investigation, Supervision, Validation, Writing –
## Review & Editing.

## CONFLICT OF INTERESTS
No conflict of interests were disclosed.

## ETHICS STATEMENTS
Our publication ethics follow The Committee of Publication Ethics (COPE) guideline.  https://publicationethics.org/

## DATA AVAILABILITY
The data that support the findings of this study are available from the corresponding author upon reasonable request.

## REFERENCES
[1]  G.  Bhatambarekar,  S.  A.  Bhinge,  K.  Bhale,  A.  Dandgaval,  and  K.  Ramteke, “A Study on Physiotherapy Exercise
Corrector,” 2022 International Conference on Smart Generation Computing, Communication and Networking (SMART
GENCON), 2022, pp. 1–6, doi:10.1109/SMARTGENCON56628.2022.10084127.
[2]  R.  K.  J.  Parasher,  S.  Singh,  V.  Sharma,  P.  Dabas,  and  S.  Vashisht, “Enhancing Exercise Form: A Pose Estimation
Approach with Body Landmark Detection,” 2024 11th International Conference on Reliability, Infocom Technologies
and Optimization (Trends and Future Directions) (ICRITO), 2024, pp. 1–6,
doi:10.1109/ICRITO61523.2024.10522133.

[3] A. Brent-Smith, “On Detecting Mistakes,” The Musical Times, vol. 73, no. 1067, Jan. 1932, p. 19, doi:10.2307/915165.

[4] K. Jantachat, P. Bua-Ngam, P. Boonsit, and W.  Boonkwang, “Development of an Exercise Posture Monitoring System
for  Air  Cadets  by  Using  MediaPipe  and  OpenCV,” 2024   21st   International   Conference   on   Electrical
Engineering/Electronics,  Computer,  Telecommunications and  Information  Technology  (ECTI-CON), 2024,  pp. 1–4,
doi:10.1109/ECTI-CON60892.2024.10594989.
[5] K. Rishabh, J. Parasher, S. Singh, V. Sharma, P. Dabas, and S. Vashisht, “Enhancing Exercise Form: A Pose Estimation
Approach with Body Landmark Detection,” 2024 11th International Conference on Reliability, Infocom Technologies
and Optimization (Trends and Future Directions) (ICRITO), 2024, pp. 1–6,
doi:10.1109/ICRITO61523.2024.10522133.
[6] A. Ashok, A. Ramalingam, and S.  Dheenadhayalan, “Personal Exercise Trainer Using Computer Vision.” 2024 Second
International Conference on Emerging Trends in Information Technology and Engineering (ICETITE), 2024, pp. 1–
6, doi:10.1109/ic-ETITE58242.2024.10493615.

[7] W. Deng, and W. Yang, “Fitness Training Assistance System Based on Mediapipe Model and KNN Algorithm,” 2024
5th International Seminar on Artificial Intelligence, Networking and Information Technology (AINIT), 2024, pp. 1878–
82, doi:10.1109/AINIT61980.2024.10581426.


Journal of Informatics and Web Engineering                Vol. 5 No.1 (February 2026)
## 250

[8] D. Rai, A. Kumar, and A. Baghel, “Pose Detection Using OpenCV and Media Pipe,” 2024 International Conference
on Integrated Circuits, Communication, and Computing Systems (ICIC3S), 2024, pp. 1–6,
doi:10.1109/ICIC3S61846.2024.10603040.

[9]     A. Bhargavan, A. Bhat, A. Gupta, K. N. Mehta, and P. Kanwal, “Pose Detection with Corrective Feedback to Aid
Physiotherapy  for  Parkinson’s  Disease,” 2024  Second  International  Conference  on  Inventive  Computing  and
Informatics (ICICI), 2024, pp. 198–205, doi:10.1109/ICICI62254.2024.00042.

[10]           D.  Bose,  B.  Arora,  A. K.  Srivastava,  and  P.  Garg “A Computer Vision Based Framework for Posture Analysis and
Performance Prediction in Athletes,” 2024  International  Conference  on  Communication,  Computer  Sciences  and
Engineering (IC3SE), 2024, pp. 942–47, doi:10.1109/IC3SE62002.2024.10593041.

[11] C.  B.  Thaokar,  V.  V.  Dongre,  H.  H.  Hiware,  and  H.  D.  Dagwar,  “Body  Posture  Recognition  And  Fitness
Training,” 2023    OITS    International    Conference    on    Information    Technology    (OCIT),    2023,    pp.    927–
32, doi:10.1109/OCIT59427.2023.10430680.

[12]  Y. Kwon, and D. Kim. “Real-Time  Workout  Posture  Correction  Using  OpenCV  and  MediaPipe,” The  Journal  of
Korean  Institute of Information Technology, vol. 20, no. 1, Jan. 2022, pp. 199–208.  doi:10.14801/jkiit.2022.20.1.199.

[13]  M. D. Korableva and Y. A. Bekeneva, “Evaluation of Physical Exercise Performance Using Deep Learning Methods,”
2024  V  International  Conference  on  Neural  Networks  and  Neurotechnologies  (NeuroNT),  2024,  pp.  93–95,
doi:10.1109/neuront62606.2024.10585349.

[14]   C.  Guo  et  al.,  “Design of  a  Sports  Rehabilitation Evaluation Scheme  Based  on MediaPipe  Technology,” 2024
International     Conference     on     Intelligent     Computing     and     Data     Mining     (ICDM),     2024,    pp.     134–
38, doi:10.1109/ICDM63232.2024.10762646.

[15]  M. Chariar, S. Rao, A. Irani, S. Suresh, and C. S. Asha, “AI Trainer: Autoencoder Based Approach for Squat Analysis
and Correction,” IEEE Access, vol. 11, 2023, pp. 107135–49, doi:10.1109/ACCESS.2023.3316009.

[16]  B. S. Cobb and F. Candan, “Improving Workplace Safety in the Cargo Industry through Posture Monitoring Using
Mediapipe  and  Machine  Learning,” 2023  International  Conference  on  Innovations  in  Intelligent  Systems  and
Applications (INISTA), 2023, pp. 1–6, doi:10.1109/INISTA59065.2023.10310609.

[17]  T. Maitray, U. Singh, V. Kukreja, A. Patel, and V. Sharma, “Exercise Posture Rectifier and Tracker Using MediaPipe
and  OpenCV,” 2023   5th   International   Conference  on   Advances  in   Computing,   Communication   Control  and
Networking (ICAC3N), 2023, pp. 141–4, doi:10.1109/ICAC3N60023.2023.10541703.

[18]  Y. Tomar, N. Himanshu, S. Devi, and H. Kaur, “Human Motion Tracker Using OpenCv and Mediapipe,” 2023 3rd
International  Conference  on  Innovative  Mechanisms  for  Industry  Applications  (ICIMIA),  2023,  pp.  1199–204,
doi:10.1109/ICIMIA60377.2023.10425865.

[19]  K. L. Joshitha, P. Madhanraj, B. R. Roshan, G. Prakash, and V. S. M. Ram, “AI-FIT  COACH - Revolutionizing
Personal  Fitness  With  Pose  Detection,  Correction  and  Smart  Guidance,” 2024   International   Conference   on
Communication, Computing and Internet of Things (IC3IoT), 2024, pp. 1–5,
doi:10.1109/IC3IoT60841.2024.10550400.

[20] H. C. Saini, “iSmartYog: A Real Time Yoga Pose Recognition and Correction Feedback Model Using Deep Learning
for Smart  Healthcare,” 2023  International  Conference  on  Smart  Systems  for  Applications  in  Electrical  Sciences
(ICSSES), 2023, pp. 1–6, doi:10.1109/ICSSES58299.2023.10201061.




Journal of Informatics and Web Engineering                Vol. 5 No.1 (February 2026)
## 251

## BIOGRAPHIES OF AUTHORS

Wan  Izzul  Wafiq is  a  final  year  student  in  Multimedia  University,  Cyberjaya,  Malaysia.  He  is
currently pursuing a bachelor’s degree in computer science specializing in Data Science. His
passion is in the data science field, and he gained experience working as a data analyst during his
internship period. He can be contacted at email: wanizzul02@gamil.com.


S. Prabha  Kumaresan is  an  Assistant  Professor  at  Multimedia  University  with  a  PhD  in
Engineering   from   MMU,   Cyberjaya.   Her   research   focuses   on   machine   learning,   artificial
intelligence, and data analytics, with applications in education and industry. She is actively involved
in  collaborative  projects  that  promote  digital  talent  development  and  is  committed  to  student
engagement and mentoring. Her goal is to prepare learners for future technologies and innovation-
driven environments. She can be contacted at email: prabha.kumaresan@mmu.edu.my.

---

## Implementación en este repositorio (referencia cruzada)

Los umbrales de sentadilla del artículo (ángulo interno cadera–rodilla–tobillo «bueno» 80–100°, «ajustar» 60–79° o 101–120°, «malo» &lt;60° o &gt;120°) se aplican en la app Flutter como **flexión de rodilla** `180° − ángulo_interno`, coherente con `vision/biomechanics.py`:

- `app/lib/pose/angle_ranges.dart` — estados bueno / advertencia / malo y constantes `squatFlex*`.
- `app/lib/core/utils/angle_formatter.dart` — progreso ROM y sublabels de métricas.
- `app/lib/views/analysis/shared/widgets/live_dashboard_panel.dart` — bandas del histórico de ángulos.
- `backend/vision/rep_trackers/squat.py` — profundidad mínima de fondo (`bottom = 80°` flexión) para conteo de repeticiones.
- `lungeFrontKneeFlexionStatus` / `lungeRearKneeFlexionStatus` y `isLungeExerciseLabel` en `angle_ranges.dart`; `kneeFlexionStatusForExercise` elige delantera vs trasera (mayor flexión = delantera).
- Flutter: cuando `exercise_label` contiene `lunge` o `zancada`, métricas, overlay de rodillas, vibración (en vivo), registro de vídeo y acumulador de sesión usan `AngleFormatter.statusForKneeFlexionInContext` / `kneeFlexionRomProgressInContext` / `kneeFlexionMetricSublabelInContext`.
