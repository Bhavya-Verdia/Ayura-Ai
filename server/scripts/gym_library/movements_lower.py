"""Curated lower-body, trunk, conditioning and mobility movements.

Three of the most commonly programmed lifts in coaching — `Goblet Squat`,
`Romanian Deadlift` and `Band Pull Apart` — were already in the library and were
prescribed exactly zero times across 28,320 generated training days, while
`Middle Back Shrug` was prescribed 1,461 times. Nothing here is exotic. The
point of the curation is that the ordinary things get picked.
"""

from .spec import M

LEGS = [
    # ---- bodyweight --------------------------------------------------------
    M("Bodyweight Squat", canonical=True, bucket="legs", pattern="squat", mechanic="compound",
      equipment="bodyweight", role="main", skill_floor="beginner",
      level="beginner", family="squat",
      cue="Sit back and down between the hips; knees track over the middle toes.",
      easier="Box Squat to a chair", harder="Bulgarian Split Squat"),

    M("Box Squat to a Chair", src=None, bucket="legs", pattern="squat",
      mechanic="compound", equipment="bodyweight", role="main",
      skill_floor="beginner", level="beginner", family="squat",
      pm=["quadriceps"], sm=["glutes", "hamstrings"],
      instructions=[
          "Stand in front of a chair or bench with the feet about shoulder-width apart.",
          "Reach the hips back and lower under control until you are seated.",
          "Keep the chest up and the weight through the mid-foot rather than the toes.",
          "Stand back up by driving through the heels, without rocking forward for momentum.",
      ],
      cue="Touch and go, do not flop. The chair sets the depth so you can build confidence in it.",
      harder="Bodyweight Squat"),

    M("Wall Sit", src=None, bucket="legs", pattern="squat", mechanic="isolation",
      equipment="bodyweight", role="accessory", skill_floor="beginner",
      level="beginner", family="wall_sit", rep_style="isometric",
      pm=["quadriceps"], sm=["glutes"],
      instructions=[
          "Stand with your back flat against a wall and walk the feet out about two foot-lengths.",
          "Slide down the wall until the knees are bent to roughly ninety degrees.",
          "Keep the shins vertical and the whole back in contact with the wall.",
          "Hold, breathing normally, then walk the feet back in to stand up.",
      ],
      cue="If the knees pass the toes, walk the feet further out.",
      easier="sit higher, with less knee bend",
      harder="Wall Sit holding a weight on the lap"),

    M("Reverse Lunge", src=None, bucket="legs", pattern="lunge",
      mechanic="compound", equipment="bodyweight", role="main",
      skill_floor="beginner", level="beginner", family="lunge", unilateral=True,
      pm=["quadriceps"], sm=["glutes", "hamstrings"],
      instructions=[
          "Stand tall with the feet hip-width apart and the hands on the hips.",
          "Step one foot back and lower until both knees are bent to about ninety degrees.",
          "Keep the front shin close to vertical and the torso upright.",
          "Drive through the front heel to return to standing, then alternate sides.",
      ],
      cue="Stepping back rather than forward is much kinder to the knee.",
      easier="Split Squat holding a support", harder="Bulgarian Split Squat"),

    M("Bulgarian Split Squat", src=None, bucket="legs", pattern="lunge",
      mechanic="compound", equipment="bodyweight", role="main",
      skill_floor="intermediate", level="intermediate", family="split_squat",
      unilateral=True, pm=["quadriceps"], sm=["glutes", "hamstrings"],
      instructions=[
          "Stand about two feet in front of a bench and place the top of one foot on it behind you.",
          "Keep the torso upright and the front foot far enough forward that the knee stays over the ankle.",
          "Lower until the back knee approaches the floor and the front thigh is roughly parallel.",
          "Drive through the front heel to stand, completing all reps before changing sides.",
      ],
      cue="Almost all the work belongs to the front leg — the back foot is for balance only.",
      easier="Reverse Lunge"),

    M("Glute Bridge", src="Butt Lift (Bridge)", bucket="legs", pattern="hinge",
      mechanic="compound", equipment="bodyweight", role="accessory",
      skill_floor="beginner", level="beginner", family="hip_thrust",
      cue="Finish with the ribs down and the glutes squeezed, not with the low back arched.",
      harder="Single Leg Glute Bridge"),

    M("Single Leg Glute Bridge", bucket="legs", pattern="hinge",
      mechanic="compound", equipment="bodyweight", role="accessory",
      skill_floor="beginner", level="beginner", family="hip_thrust",
      unilateral=True,
      cue="Keep the hips level — the side that drops is the one that needs the work.",
      easier="Glute Bridge",
      harder="Barbell Hip Thrust"),

    M("Standing Calf Raise", src="Standing Calf Raises", bucket="legs",
      pattern="isolation", mechanic="isolation", equipment="bodyweight",
      role="accessory", skill_floor="beginner", level="beginner",
      family="calf_raise",
      cue="Full range, slow down. Calves answer to time under tension, not to bouncing.",
      easier="both feet on flat ground",
      harder="single-leg calf raise off a step"),

    # ---- dumbbell / kettlebell --------------------------------------------
    M("Goblet Squat", canonical=True, bucket="legs", pattern="squat", mechanic="compound",
      equipment="dumbbell", role="main", load_class="front_squat",
      skill_floor="beginner", level="beginner", family="squat",
      cue="Holding the weight at the chest keeps you upright — it is the best squat to learn on."),

    M("Dumbbell Lunges", canonical=True, bucket="legs", pattern="lunge", mechanic="compound",
      equipment="dumbbell", role="main", load_class="lunge",
      skill_floor="beginner", level="beginner", family="lunge", unilateral=True,
      instructions=[
          "Stand tall with a dumbbell hanging at each side and the feet hip-width apart.",
          "Take a controlled step forward, about two-thirds of a metre, and lower the back knee toward the floor.",
          "Stop when both knees are bent to roughly ninety degrees and the front shin is close to vertical.",
          "Drive through the front heel to push back to the starting position.",
          "Alternate legs, keeping the torso upright and the dumbbells hanging still.",
      ],
      cue="Weights hang at the sides; let the legs do the work, not the shoulders."),

    M("Dumbbell Romanian Deadlift", src="Romanian Deadlift", bucket="legs",
      pattern="hinge", mechanic="compound", equipment="dumbbell", role="main",
      load_class="romanian_deadlift", skill_floor="beginner", level="beginner",
      family="romanian_deadlift", contra=["lower_back_pain", "herniated_disc"],
      cue="Push the hips back and keep the weights against the thighs. Stop when the hamstrings run out."),

    M("Dumbbell Step Ups", bucket="legs", pattern="lunge", mechanic="compound",
      equipment="dumbbell", role="accessory", load_class="step_up",
      skill_floor="beginner", level="beginner", family="step_up", unilateral=True,
      cue="Step down under control — that is the half everyone rushes."),

    M("Kettlebell Swing", src="Kettlebell Swing (Cardio)",
      bucket="legs", pattern="hinge", mechanic="compound", equipment="kettlebell",
      role="accessory", load_class="kettlebell_swing", skill_floor="intermediate",
      level="intermediate", family="swing", impact="none",
      contra=["lower_back_pain", "herniated_disc", "hypertension"],
      cue="It is a hinge, not a squat, and the arms are rope — the hips throw the bell."),

    # ---- barbell -----------------------------------------------------------
    M("Barbell Squat", canonical=True, bucket="legs", pattern="squat", mechanic="compound",
      equipment="barbell", role="main", load_class="back_squat",
      skill_floor="beginner", level="beginner", family="squat",
      contra=["bad_knee", "herniated_disc", "knee_replacement"],
      cue="Brace as if about to be punched, then sit between the hips.",
      easier="Goblet Squat"),

    M("Front Barbell Squat", bucket="legs", pattern="squat", mechanic="compound",
      equipment="barbell", role="accessory", load_class="front_squat",
      skill_floor="advanced", level="advanced", family="squat",
      contra=["bad_knee", "knee_replacement", "shoulder_injury"],
      cue="Elbows high throughout — the moment they drop, the bar follows."),

    M("Barbell Deadlift", src="Barbell Deadlift", canonical=True, bucket="legs", pattern="hinge",
      mechanic="compound", equipment="barbell", role="main",
      load_class="deadlift", skill_floor="beginner", level="intermediate",
      family="deadlift", contra=["lower_back_pain", "herniated_disc", "hypertension"],
      cue="The bar stays against the legs the whole way. If it swings out, reset."),

    M("Barbell Romanian Deadlift", src="Romanian Deadlift", canonical=True, bucket="legs",
      pattern="hinge", mechanic="compound", equipment="barbell", role="main",
      load_class="romanian_deadlift", skill_floor="beginner",
      level="intermediate", family="romanian_deadlift",
      contra=["lower_back_pain", "herniated_disc"],
      cue="Soft knees, long spine, hips travel back — this is a hamstring movement, not a squat."),

    M("Barbell Hip Thrust", bucket="legs", pattern="hinge", mechanic="compound",
      equipment="barbell", role="accessory", load_class="hip_thrust",
      skill_floor="intermediate", level="intermediate", family="hip_thrust",
      cue="Chin tucked, ribs down, and finish with the hips level with the knees."),

    M("Barbell Lunge", bucket="legs", pattern="lunge", mechanic="compound",
      equipment="barbell", role="accessory", load_class="lunge",
      skill_floor="advanced", level="advanced", family="lunge", unilateral=True,
      contra=["bad_knee", "knee_replacement"],
      cue="Balance is the limiting factor here, not strength. Go lighter than you think."),

    # ---- machine -----------------------------------------------------------
    M("Leg Press", canonical=True, bucket="legs", pattern="squat", mechanic="compound",
      equipment="machine", role="main", load_class="leg_press",
      skill_floor="beginner", level="beginner", family="leg_press",
      contra=["bad_knee", "herniated_disc"],
      cue="Do not let the low back round off the pad at the bottom — that is the depth limit."),

    M("Leg Extensions", bucket="legs", pattern="isolation", mechanic="isolation",
      equipment="machine", role="accessory", load_class="leg_extension",
      skill_floor="beginner", level="beginner", family="leg_extension",
      contra=["bad_knee", "knee_replacement"],
      cue="Pause at the top. Swinging up and dropping down is where knees complain."),

    M("Lying Leg Curls", bucket="legs", pattern="isolation", mechanic="isolation",
      equipment="machine", role="accessory", load_class="leg_curl",
      skill_floor="beginner", level="beginner", family="leg_curl",
      cue="Hips stay down on the pad; lifting them means the weight is too heavy."),

    M("Seated Calf Raise", bucket="legs", pattern="isolation", mechanic="isolation",
      equipment="machine", role="accessory", load_class="calf_raise",
      skill_floor="beginner", level="beginner", family="calf_raise",
      cue="Bent knee shifts the work to the soleus — the deeper calf muscle."),
]

CORE = [
    M("Plank", bucket="core", pattern="anti_extension", mechanic="isolation",
      equipment="bodyweight", role="accessory", skill_floor="beginner",
      level="beginner", family="plank", rep_style="isometric",
      instructions=[
          "Lie face down and set the forearms on the floor with the elbows directly under the shoulders.",
          "Tuck the toes under and lift the hips until the body is one straight line from head to heels.",
          "Squeeze the glutes and brace the trunk as if about to be punched in the stomach.",
          "Hold, breathing normally through the nose, without letting the hips sag or ride up.",
          "Lower the knees to the floor to finish rather than collapsing out of the position.",
      ],
      cue="Squeeze glutes and quads. A plank you can hold for three minutes is too easy.",
      easier="Plank from the knees", harder="Plank with one foot lifted"),

    M("Side Plank", src=None, bucket="core", pattern="anti_rotation",
      mechanic="isolation", equipment="bodyweight", role="accessory",
      skill_floor="beginner", level="beginner", family="side_plank",
      rep_style="isometric", unilateral=True,
      pm=["abdominals"], sm=["shoulders", "glutes"],
      instructions=[
          "Lie on one side with the forearm on the floor and the elbow under the shoulder.",
          "Stack the feet, or stagger them for a wider base.",
          "Press the forearm down and lift the hips until the body is a straight line.",
          "Hold, breathing normally, then lower under control and change sides.",
      ],
      cue="Stack the shoulders and hips; do not let the top one roll forward.",
      easier="drop to the bottom knee for support",
      harder="Side Plank with the top leg raised"),

    M("Dead Bug", bucket="core", pattern="anti_extension", mechanic="isolation",
      equipment="bodyweight", role="accessory", skill_floor="beginner",
      level="beginner", family="dead_bug",
      cue="Low back stays pressed to the floor the whole time. That is the entire exercise.",
      easier="keep the knees bent and move one limb at a time",
      harder="Hollow Body Hold"),

    M("Bird Dog", bucket="core", pattern="anti_rotation", mechanic="isolation",
      equipment="bodyweight", role="accessory", skill_floor="beginner",
      level="beginner", family="bird_dog", unilateral=True,
      cue="Reach long rather than high, and keep the hips square to the floor.",
      easier="extend only the arm, or only the leg",
      harder="Bird Dog with a pause at full extension"),

    M("Crunches", bucket="core", pattern="isolation", mechanic="isolation",
      equipment="bodyweight", role="accessory", skill_floor="beginner",
      level="beginner", family="crunch",
      contra=["herniated_disc", "lower_back_pain"],
      cue="Curl the ribs toward the hips; do not yank on your own neck.",
      harder="Cable Crunch"),

    M("Hanging Leg Raise", bucket="core", pattern="anti_extension",
      mechanic="isolation", equipment="bodyweight", role="accessory",
      skill_floor="advanced", level="intermediate", family="leg_raise",
      cue="Tilt the pelvis before the legs move, or the hip flexors take all of it.",
      easier="Lying Leg Raise"),

    M("Lying Leg Raise", src="Flat Bench Leg Pull-In", bucket="core",
      pattern="anti_extension", mechanic="isolation", equipment="bodyweight",
      role="accessory", skill_floor="beginner", level="beginner",
      family="leg_raise", contra=["lower_back_pain", "herniated_disc"],
      cue="Hands under the hips, low back flat. Shorten the range before you let it arch.",
      easier="bend the knees to shorten the lever",
      harder="Leg Raise on Parallel Bars"),

    M("Pallof Press", bucket="core", pattern="anti_rotation", mechanic="isolation",
      equipment="cable", role="accessory", load_class="pallof",
      skill_floor="beginner", level="beginner", family="pallof", unilateral=True,
      cue="The point is to NOT rotate. Stand far enough out that resisting is hard."),

    M("Farmer's Walk", src=None, bucket="core", pattern="carry",
      mechanic="compound", equipment="dumbbell", role="accessory",
      load_class="farmers_carry", skill_floor="beginner", level="beginner",
      family="carry", rep_style="distance",
      pm=["core"], sm=["traps", "forearms", "glutes"],
      instructions=[
          "Set a pair of heavy dumbbells or kettlebells on the floor at your sides.",
          "Hinge at the hips to pick them up, keeping the chest up and the spine long.",
          "Stand tall with the shoulders back and the ribs down, arms hanging at your sides.",
          "Walk in a straight line with controlled steps for the prescribed distance.",
          "Set the weights down under control rather than dropping them.",
      ],
      cue="Walk tall and do not let the weights swing. It trains the trunk and the grip together."),
]

CONDITIONING = [
    M("Brisk Walking", bucket="cardio", pattern="locomotion", mechanic="compound",
      equipment="bodyweight", role="finisher", skill_floor="beginner",
      level="beginner", family="walk", rep_style="time", category="cardio",
      impact="low", cal_per_min=5,
      cue="Fast enough that talking takes effort; slow enough that you could still do it."),

    M("Stationary Cycling", src="Bicycling, Stationary", bucket="cardio",
      pattern="locomotion", mechanic="compound", equipment="stationary_bike",
      role="finisher", skill_floor="beginner", level="beginner",
      rep_style="time", category="cardio", family="cycle", impact="none",
      cal_per_min=8,
      instructions=[
          "Set the saddle so that at the bottom of the pedal stroke the knee is almost straight, with a slight bend.",
          "Sit tall with a light grip on the handlebars and the shoulders relaxed.",
          "Pedal easily for two to three minutes to warm up before adding resistance.",
          "Raise the resistance until the effort is moderate and sustainable, keeping a smooth cadence.",
          "Ease the resistance off for the last few minutes to cool down.",
      ],
      cue="Low impact and easy to regulate — the default when joints are the limit."),

    M("Rowing Machine", src="Rowing, Stationary", bucket="cardio",
      pattern="locomotion", mechanic="compound", equipment="rowing_machine",
      role="finisher", skill_floor="intermediate", level="intermediate",
      rep_style="time", category="cardio", family="row_erg", impact="none",
      contra=["lower_back_pain", "herniated_disc"], cal_per_min=10,
      cue="Legs, then back, then arms — and the reverse on the way in."),

    M("Elliptical Trainer", bucket="cardio", pattern="locomotion",
      mechanic="compound", equipment="elliptical", role="finisher",
      skill_floor="beginner", level="beginner", rep_style="time",
      category="cardio", family="elliptical", impact="none", cal_per_min=8,
      instructions=[
          "Step onto the pedals and hold the moving handles with a light grip, standing tall.",
          "Start pedalling at an easy pace for two to three minutes to warm up.",
          "Raise the resistance until the effort feels moderate but you could still speak in short sentences.",
          "Keep the whole foot in contact with the pedal and drive with the legs rather than pulling with the arms.",
          "Lower the resistance for the final two minutes to bring the breathing back down.",
      ],
      cue="Supported and low impact, which is why it survives most joint restrictions."),

    M("Jump Rope", src="Rope Jumping", bucket="cardio", pattern="locomotion",
      mechanic="compound", equipment="jump_rope", role="finisher",
      skill_floor="intermediate", level="intermediate", rep_style="time",
      category="cardio", family="jump_rope", impact="high",
      contra=["hypertension", "heart_disease", "bad_knee", "knee_replacement"],
      cal_per_min=12,
      instructions=[
          "Hold a handle in each hand with the rope resting on the floor behind your heels.",
          "Set the elbows close to the ribs and turn the rope with the wrists, not the whole arm.",
          "Jump about an inch off the ground off the balls of the feet as the rope comes round.",
          "Land softly with the knees slightly bent and keep the turning pace steady.",
          "Start with short bouts of twenty to thirty seconds and build up as the coordination comes.",
      ],
      cue="Small hops off the balls of the feet — an inch is plenty."),

    M("High Knees", bucket="cardio", pattern="locomotion", mechanic="compound",
      equipment="bodyweight", role="finisher", skill_floor="beginner",
      level="beginner", rep_style="time", category="cardio", impact="high",
      family="high_knees", contra=["hypertension", "heart_disease", "bad_knee"],
      cal_per_min=11, cue="Drive the knees to hip height and stay light on the feet."),

    M("Jumping Jacks", bucket="cardio", pattern="locomotion", mechanic="compound",
      equipment="bodyweight", role="finisher", skill_floor="beginner",
      level="beginner", rep_style="time", category="cardio", impact="high",
      family="jumping_jack", contra=["bad_knee", "knee_replacement"],
      cal_per_min=10, cue="Land softly through the whole foot, knees slightly bent."),

    M("Mountain Climbers", bucket="cardio", pattern="locomotion",
      mechanic="compound", equipment="bodyweight", role="finisher",
      skill_floor="beginner", level="beginner", rep_style="time",
      category="cardio", impact="low", family="mountain_climber",
      contra=["hypertension", "heart_disease", "shoulder_injury"], cal_per_min=11,
      instructions=[
          "Start in a push-up position with the hands under the shoulders and the body in a straight line.",
          "Brace the trunk and draw one knee toward the chest without letting the hips rise.",
          "Switch legs, driving the other knee forward as the first foot returns to the floor.",
          "Keep alternating at a steady rhythm, breathing continuously, for the prescribed time.",
          "Keep the shoulders stacked over the hands throughout rather than drifting behind them.",
      ],
      cue="Hips stay low and level; do not let them bounce up with each drive."),

    M("Burpees", src="Burpee", bucket="cardio", pattern="locomotion", mechanic="compound",
      equipment="bodyweight", role="finisher", skill_floor="intermediate",
      level="intermediate", rep_style="time", category="cardio", impact="high",
      family="burpee", contra=["hypertension", "heart_disease", "bad_knee",
                               "knee_replacement", "shoulder_injury"],
      cal_per_min=14, cue="Pace it. Burpees punish anyone who starts at a sprint."),

    M("Stair Climbing", src="Stairmaster", bucket="cardio", pattern="locomotion",
      mechanic="compound", equipment="stair_climber", role="finisher",
      skill_floor="beginner", level="beginner", rep_style="time",
      category="cardio", family="stairs", impact="low",
      contra=["bad_knee", "knee_replacement"], cal_per_min=9,
      instructions=[
          "Step onto the machine and start at a slow pace to find your rhythm.",
          "Stand tall with the shoulders back and let the hands rest lightly on the rails for balance only.",
          "Take full steps, driving through the whole foot rather than the toes.",
          "Raise the speed until the effort is moderate and you could still speak in short sentences.",
          "Ease the pace back for the final two minutes to bring the heart rate down.",
      ],
      cue="Stand tall and stay off the handrails — leaning on them halves the work."),

    M("Swimming", src=None, bucket="cardio", pattern="locomotion",
      mechanic="compound", equipment="pool", role="finisher",
      skill_floor="intermediate", level="beginner", rep_style="time",
      category="cardio", family="swim", impact="none", cal_per_min=10,
      pm=["cardiovascular system"], sm=["lats", "shoulders", "legs"],
      instructions=[
          "Warm up with two to three easy lengths at a conversational pace.",
          "Swim at a steady effort you could sustain, breathing on a regular rhythm.",
          "Rest for twenty to thirty seconds at the wall whenever you need to.",
          "Finish with a slow length to bring the breathing back down.",
      ],
      cue="The most joint-friendly conditioning there is, which is why it survives almost every restriction."),
]

# Mobility and warm-up drills. These are the entries that used to be filed as
# `strength` and prescribed as working sets with sets, reps and a weight range —
# 46% of training days contained at least one. They are kept, because a session
# needs a warm-up, and they are fenced: `role` puts them out of reach of the
# working slots entirely.
MOBILITY = [
    M("Arm Circles", bucket="shoulders", pattern="rotation", mechanic="isolation",
      equipment="bodyweight", role="warmup", category="stretching",
      family="arm_circle", rep_style="time",
      instructions=[
          "Stand tall with the feet hip-width apart and the arms extended out to the sides at shoulder height.",
          "Make small circles forward, about the size of a dinner plate, keeping the arms long.",
          "Gradually widen the circles over ten to fifteen seconds.",
          "Reverse the direction and repeat, keeping the shoulders down away from the ears.",
      ],
      cue="Small circles first, then larger — this is joint preparation, not a set."),

    M("Standing Hip Circles", bucket="legs", pattern="rotation",
      mechanic="isolation", equipment="bodyweight", role="warmup",
      category="stretching", family="hip_circle", rep_style="time",
      cue="Hold a support if you need it and keep the circles slow."),

    M("Inchworm", bucket="full_body", pattern="locomotion", mechanic="compound",
      equipment="bodyweight", role="warmup", category="stretching",
      family="inchworm", cue="Walk the hands out to a plank and back; keep the legs as straight as comfort allows."),

    M("Cat-Cow", src=None, bucket="core", pattern="rotation", mechanic="isolation",
      equipment="bodyweight", role="warmup", category="stretching",
      family="cat_cow", rep_style="time", pm=["lower back"], sm=["abdominals"],
      instructions=[
          "Start on hands and knees with the wrists under the shoulders and knees under the hips.",
          "Inhale and let the belly drop as you lift the chest and tailbone.",
          "Exhale and round the spine, drawing the chin and tailbone toward each other.",
          "Move slowly with the breath rather than forcing either end of the range.",
      ],
      cue="Let the breath set the pace — inhale to arch, exhale to round."),

    M("90/90 Hamstring", bucket="legs", pattern="isolation", mechanic="isolation",
      equipment="bodyweight", role="mobility", category="stretching",
      family="hamstring_stretch", rep_style="time",
      cue="Hold thirty seconds and breathe. A stretch is not a set."),

    M("Adductor", bucket="legs", pattern="isolation", mechanic="isolation",
      equipment="bodyweight", role="mobility", category="stretching",
      family="adductor_stretch", rep_style="time",
      cue="Ease into it. Bouncing at the end range achieves nothing."),

    M("Lying Prone Quadriceps", bucket="legs", pattern="isolation",
      mechanic="isolation", equipment="bodyweight", role="mobility",
      category="stretching", family="quad_stretch", rep_style="time",
      cue="Keep the knees together and the hips square."),

    M("Child's Pose", src="Child'S Pose", bucket="core", pattern="isolation",
      mechanic="isolation", equipment="bodyweight", role="mobility",
      category="stretching", family="childs_pose", rep_style="time",
      cue="Let the breath widen the back of the ribs."),

    M("Wrist Circles", bucket="full_body", pattern="rotation",
      mechanic="isolation", equipment="bodyweight", role="warmup",
      category="stretching", family="wrist_circle", rep_style="time",
      cue="Thirty seconds before anything that loads the wrist."),

    M("Seated Glute", bucket="legs", pattern="isolation", mechanic="isolation",
      equipment="bodyweight", role="mobility", category="stretching",
      family="glute_stretch", rep_style="time",
      cue="Sit tall and hinge forward from the hips, not the low back."),
]
