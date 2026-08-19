"""Movements that fill the cells the first pass left thin.

Written against the builder's own coverage report rather than from memory: a
`(bucket, equipment tier)` holding fewer than three working options is a cell
where a four-week plan has to repeat itself, and repetition is what the old
library's five bodyweight back exercises produced.
"""

from .spec import M

FILL_CHEST = [
    M("Close-Grip Bench Press", src="Barbell Bench Press - Medium Grip",
      bucket="triceps", pattern="push_h", mechanic="compound",
      equipment="barbell", role="main", load_class="bench_press",
      skill_floor="intermediate", level="intermediate", family="bench_press",
      contra=["elbow_injury"],
      cue="Hands just inside shoulder width. Any closer and the wrists pay for it."),

    M("Barbell Floor Press", src="Floor Press", bucket="chest", pattern="push_h",
      mechanic="compound", equipment="barbell", role="accessory",
      load_class="floor_press", skill_floor="intermediate", level="intermediate",
      family="floor_press",
      cue="Pause when the triceps touch the floor rather than bouncing off it."),

    M("Dip Machine", bucket="chest", pattern="push_v", mechanic="compound",
      equipment="machine", role="accessory", load_class="dip",
      skill_floor="beginner", level="beginner", family="dip",
      contra=["shoulder_injury"],
      cue="The assisted version of a dip — use it to build toward the real thing."),
]

FILL_BACK = [
    M("T-Bar Row", src="T-Bar Row With Handle", bucket="back", pattern="pull_h",
      mechanic="compound", equipment="barbell", role="main",
      load_class="barbell_row", skill_floor="intermediate", level="intermediate",
      family="barbell_row", contra=["lower_back_pain", "herniated_disc"],
      cue="Chest supported where possible — it takes the low back out of the equation."),

    M("Rack Pull", src="Rack Pulls", bucket="back", pattern="hinge",
      mechanic="compound", equipment="barbell", role="accessory",
      load_class="deadlift", skill_floor="advanced", level="advanced",
      family="deadlift", contra=["lower_back_pain", "herniated_disc", "hypertension"],
      cue="Bar starts at knee height. It is a deadlift with the hardest part removed."),

    M("Back Extension", src="Hyperextensions (Back Extensions)", bucket="back",
      pattern="hinge", mechanic="compound", equipment="bodyweight",
      role="accessory", skill_floor="beginner", level="beginner",
      family="back_extension", contra=["herniated_disc"],
      cue="Stop at a straight line. Arching past it is where this goes wrong.",
      harder="Back Extension holding a plate to the chest"),

    M("Chest Supported Dumbbell Row", src="Dumbbell Incline Row", bucket="back",
      pattern="pull_h", mechanic="compound", equipment="dumbbell",
      role="main", load_class="chest_supported_row", skill_floor="beginner",
      level="beginner", family="db_row",
      cue="The bench holds your torso so the back does all the pulling."),

    M("Renegade Row", src="Alternating Renegade Row", bucket="back",
      pattern="pull_h", mechanic="compound", equipment="dumbbell",
      role="accessory", load_class="chest_supported_row",
      skill_floor="advanced", level="advanced", family="db_row", unilateral=True,
      cue="Widen the feet for stability and refuse to let the hips rotate."),

    M("Cable Rear Delt Fly", bucket="shoulders", pattern="pull_h",
      mechanic="isolation", equipment="cable", role="accessory",
      load_class="rear_delt", skill_floor="beginner", level="beginner",
      family="rear_delt",
      cue="Constant tension is the advantage the cable has over dumbbells here."),

    M("Reverse Flyes", bucket="shoulders", pattern="pull_h", mechanic="isolation",
      equipment="dumbbell", role="accessory", load_class="rear_delt",
      skill_floor="beginner", level="beginner", family="rear_delt",
      cue="Thumbs down, elbows soft, and stop when the arms reach shoulder line."),
]

FILL_SHOULDERS = [
    M("Push Press", src=None, bucket="shoulders", pattern="push_v",
      mechanic="compound", equipment="barbell", role="main",
      load_class="push_press", skill_floor="advanced", level="advanced",
      family="overhead_press",
      contra=["shoulder_injury", "hypertension", "herniated_disc"],
      pm=["shoulders"], sm=["triceps", "quadriceps", "glutes"],
      instructions=[
          "Take a barbell from a rack at shoulder height with the hands just outside the shoulders.",
          "Stand tall with the elbows slightly in front of the bar and the trunk braced.",
          "Dip a few inches by bending the knees, keeping the torso upright.",
          "Drive up hard through the legs and let that momentum start the bar overhead.",
          "Finish the movement with the arms until the bar is locked out above the mid-foot.",
          "Lower the bar back to the shoulders under control and reset before the next rep.",
      ],
      cue="A short dip and drive from the legs, then the arms finish it overhead."),

    M("Cable Lateral Raise", src="Cable Seated Lateral Raise", bucket="shoulders",
      pattern="isolation", mechanic="isolation", equipment="cable",
      role="accessory", load_class="lateral_raise", skill_floor="beginner",
      level="beginner", family="lateral_raise",
      cue="Same movement as the dumbbell version, with tension at the bottom too."),

    M("Machine Shoulder Press", src="Machine Shoulder (Military) Press",
      bucket="shoulders", pattern="push_v", mechanic="compound",
      equipment="machine", role="main", load_class="overhead_press",
      skill_floor="beginner", level="beginner", family="overhead_press",
      cue="The supported option — a good place to press from if balance is the limit."),

    M("Prone Y-Raise", src=None, bucket="shoulders", pattern="isolation",
      mechanic="isolation", equipment="bodyweight", role="accessory",
      skill_floor="beginner", level="beginner", family="prone_raise",
      pm=["shoulders"], sm=["middle back", "traps"],
      instructions=[
          "Lie face down on a mat or an incline bench with the arms extended overhead in a Y shape.",
          "Turn the thumbs up toward the ceiling.",
          "Lift both arms a few inches by squeezing the muscles between the shoulder blades.",
          "Hold for a second at the top, then lower slowly without letting the hands touch down.",
      ],
      cue="Height is not the goal. Two inches done well beats six done with the low back.",
      easier="Prone T-Raise",
      harder="Reverse Flyes"),

    M("Wall Handstand Hold", src=None, bucket="shoulders", pattern="push_v",
      mechanic="compound", equipment="bodyweight", role="accessory",
      skill_floor="advanced", level="advanced", family="handstand",
      rep_style="isometric", contra=["hypertension", "shoulder_injury"],
      pm=["shoulders"], sm=["triceps", "core"],
      instructions=[
          "Place the hands about a foot from a wall, shoulder-width apart.",
          "Walk the feet up the wall until the body is close to vertical and the arms are straight.",
          "Push the floor away, keep the ribs down and hold, breathing steadily.",
          "Walk back down under control before the shoulders give out.",
      ],
      cue="Come down before you have to. This one does not warn you twice.",
      easier="Pike Push-Up - Feet Elevated"),
]

FILL_ARMS = [
    M("EZ-Bar Curl", bucket="biceps", pattern="isolation", mechanic="isolation",
      equipment="barbell", role="accessory", load_class="curl",
      skill_floor="beginner", level="beginner", family="curl",
      cue="The angled bar is easier on the wrists than a straight one."),

    M("Standing Dumbbell Reverse Curl", bucket="biceps", pattern="isolation",
      mechanic="isolation", equipment="dumbbell", role="accessory",
      load_class="preacher_curl", skill_floor="beginner", level="intermediate",
      family="reverse_curl",
      cue="Overhand grip. Go lighter than a normal curl — the forearm is the limit."),

    M("Concentration Curls", bucket="biceps", pattern="isolation",
      mechanic="isolation", equipment="dumbbell", role="accessory",
      load_class="curl", skill_floor="beginner", level="beginner",
      family="concentration_curl", unilateral=True,
      cue="Elbow braced on the thigh; no swinging available, which is the idea."),

    M("Cable Curl", src="Standing Biceps Cable Curl", bucket="biceps",
      pattern="isolation", mechanic="isolation", equipment="cable",
      role="accessory", load_class="curl", skill_floor="beginner",
      level="beginner", family="curl",
      cue="Tension never drops, so the last two reps are honest."),

    M("Inverted Row - Underhand Grip", src=None, bucket="biceps",
      pattern="pull_h", mechanic="compound", equipment="bodyweight",
      role="accessory", skill_floor="beginner", level="beginner", family="bodyweight_row",
      pm=["biceps"], sm=["lats", "middle back"],
      instructions=[
          "Set a bar at roughly hip height and lie underneath it.",
          "Take an underhand grip about shoulder-width apart, palms facing you.",
          "Walk the feet out until the body is straight and the arms are extended.",
          "Pull the chest to the bar, leading with the elbows and keeping the hips level.",
          "Lower under control until the arms are straight again.",
      ],
      cue="The underhand grip is what puts the biceps in charge of a bodyweight pull.",
      easier="set the bar higher",
      harder="Chin-Up"),

    M("EZ-Bar Skullcrusher", bucket="triceps", pattern="isolation",
      mechanic="isolation", equipment="barbell", role="accessory",
      load_class="skullcrusher", skill_floor="intermediate", level="intermediate",
      family="triceps_extension", contra=["elbow_injury"],
      cue="Upper arms angled slightly back keeps tension on through the top."),

    M("Tricep Dumbbell Kickback", bucket="triceps", pattern="isolation",
      mechanic="isolation", equipment="dumbbell", role="accessory",
      load_class="triceps_extension", skill_floor="beginner", level="beginner",
      family="kickback", unilateral=True,
      cue="Upper arm parallel to the floor and still; only the forearm moves."),

    M("Triceps Overhead Extension with Rope", bucket="triceps",
      pattern="isolation", mechanic="isolation", equipment="cable",
      role="accessory", load_class="triceps_extension", skill_floor="beginner",
      level="beginner", family="triceps_extension", contra=["shoulder_injury"],
      cue="Overhead position stretches the long head — the part pushdowns miss."),

    M("Diamond Push-Up", src=None, bucket="triceps", pattern="push_h",
      mechanic="compound", equipment="bodyweight", role="accessory",
      skill_floor="advanced", level="intermediate", family="push_up",
      contra=["elbow_injury", "wrist_injury"],
      pm=["triceps"], sm=["chest", "shoulders"],
      instructions=[
          "Start in a push-up position and bring the hands together so index fingers and thumbs form a diamond.",
          "Set the hands under the chest rather than under the face.",
          "Lower the chest toward the hands, keeping the elbows tracking back rather than flaring.",
          "Press back up to straight arms without letting the hips sag.",
      ],
      cue="Hard on the wrists — drop to the knees before you compromise the position.",
      easier="Close-Grip Push-Up"),

    M("Dumbbell Overhead Triceps Extension - Two Hands",
      src="Standing Dumbbell Triceps Extension", bucket="triceps",
      pattern="isolation", mechanic="isolation", equipment="dumbbell",
      role="accessory", load_class="triceps_extension", skill_floor="beginner",
      level="beginner", family="triceps_extension", contra=["shoulder_injury"],
      cue="One dumbbell in both hands is steadier than two, especially when heavy."),
]

FILL_LEGS = [
    M("Hack Squat", bucket="legs", pattern="squat", mechanic="compound",
      equipment="machine", role="main", load_class="hack_squat",
      skill_floor="beginner", level="intermediate", family="squat",
      contra=["bad_knee", "knee_replacement"],
      cue="Back flat on the pad throughout; the machine holds the position for you."),

    M("Sumo Deadlift", bucket="legs", pattern="hinge", mechanic="compound",
      equipment="barbell", role="main", load_class="deadlift",
      skill_floor="advanced", level="advanced", family="deadlift",
      contra=["lower_back_pain", "herniated_disc", "hypertension", "hip_injury"],
      cue="Wide stance, hands inside the knees, and open the hips as you pull."),

    M("Good Morning", bucket="legs", pattern="hinge", mechanic="compound",
      equipment="barbell", role="accessory", load_class="good_morning",
      skill_floor="advanced", level="advanced", family="good_morning",
      contra=["lower_back_pain", "herniated_disc", "hypertension"],
      cue="Go far lighter than feels necessary. This one has a very short honest range."),

    M("Seated Leg Curl", bucket="legs", pattern="isolation", mechanic="isolation",
      equipment="machine", role="accessory", load_class="leg_curl",
      skill_floor="beginner", level="beginner", family="leg_curl",
      cue="Pause at full contraction rather than snapping back."),

    M("Glute Kickback", bucket="legs", pattern="hinge", mechanic="isolation",
      equipment="bodyweight", role="accessory", skill_floor="beginner",
      level="beginner", family="kickback", unilateral=True,
      cue="Square the hips and drive the heel to the ceiling; keep the range small.",
      harder="Band Pull-Through"),

    M("Split Squat", src="Dumbbell Rear Lunge", bucket="legs", pattern="lunge",
      mechanic="compound", equipment="dumbbell", role="accessory",
      load_class="split_squat", skill_floor="beginner", level="beginner",
      family="split_squat", unilateral=True,
      cue="Feet stay planted; you are moving straight up and down, not stepping."),

    M("Barbell Step Ups", bucket="legs", pattern="lunge", mechanic="compound",
      equipment="barbell", role="accessory", load_class="step_up",
      skill_floor="advanced", level="advanced", family="step_up", unilateral=True,
      contra=["bad_knee", "knee_replacement"],
      cue="Box height at or below knee level; higher turns it into a balance test."),

    M("Calf Raises - With Bands", bucket="legs", pattern="isolation",
      mechanic="isolation", equipment="bands", role="accessory",
      skill_floor="beginner", level="beginner", family="calf_raise",
      cue="Bands are enough here — calves care more about reps than load.",
      harder="Standing Calf Raise on a step for full range"),

    M("Banded Squat", src=None, bucket="legs",
      pattern="squat", mechanic="compound", equipment="bands", role="main",
      skill_floor="beginner", level="beginner", family="squat",
      pm=["quadriceps"], sm=["glutes", "hamstrings"],
      instructions=[
          "Stand on the middle of a resistance band with the feet shoulder-width apart.",
          "Bring the top of the band over the shoulders and hold it in place at chest height.",
          "Sit back and down into a squat, keeping the chest up and the knees tracking over the toes.",
          "Drive through the heels to stand, resisting the band's pull all the way up.",
      ],
      cue="The band gets harder as you stand, which suits the squat well.",
      easier="Bodyweight Squat",
      harder="Goblet Squat"),

    M("Banded Romanian Deadlift", src=None, bucket="legs", pattern="hinge",
      mechanic="compound", equipment="bands", role="main",
      skill_floor="beginner", level="beginner", family="romanian_deadlift",
      contra=["lower_back_pain", "herniated_disc"],
      pm=["hamstrings"], sm=["glutes", "lower back"],
      instructions=[
          "Stand on the middle of a resistance band with the feet hip-width apart.",
          "Hold an end in each hand with the arms straight and the shoulders back.",
          "Push the hips back and let the hands travel down the front of the legs, knees soft.",
          "Stop when you feel the hamstrings lengthen, then drive the hips forward to stand tall.",
      ],
      cue="Hips back, not knees down. The band should stay against your legs.",
      easier="a lighter band",
      harder="Dumbbell Romanian Deadlift"),
]

FILL_CORE = [
    M("Cable Crunch", bucket="core", pattern="isolation", mechanic="isolation",
      equipment="cable", role="accessory", load_class="weighted_crunch",
      skill_floor="beginner", level="intermediate", family="crunch",
      contra=["herniated_disc", "lower_back_pain"],
      cue="Curl the spine down rather than folding at the hips."),

    M("Standing Cable Wood Chop", bucket="core", pattern="rotation",
      mechanic="compound", equipment="cable", role="accessory",
      load_class="cable_woodchop", skill_floor="intermediate",
      level="intermediate", family="woodchop", unilateral=True,
      cue="Rotate through the hips and mid-back, not the low back."),

    M("Suitcase Carry", src=None, bucket="core", pattern="carry",
      mechanic="compound", equipment="dumbbell", role="accessory",
      load_class="suitcase_carry", skill_floor="beginner", level="beginner",
      family="carry", rep_style="distance", unilateral=True,
      pm=["core"], sm=["forearms", "glutes", "traps"],
      instructions=[
          "Stand a heavy dumbbell or kettlebell on the floor beside one foot.",
          "Hinge at the hips to pick it up in one hand, keeping the chest up.",
          "Stand tall with the shoulders level — resist the pull to one side.",
          "Walk in a straight line for the prescribed distance, then swap hands.",
      ],
      cue="Staying square against a load on one side is the whole exercise."),

    M("Dumbbell Side Bend", bucket="core", pattern="isolation",
      mechanic="isolation", equipment="dumbbell", role="accessory",
      load_class="side_bend", skill_floor="beginner", level="beginner",
      family="side_bend", unilateral=True,
      contra=["herniated_disc", "lower_back_pain"],
      cue="One dumbbell only — holding two cancels the movement out."),

    M("Russian Twist", bucket="core", pattern="rotation", mechanic="isolation",
      equipment="bodyweight", role="accessory", skill_floor="beginner",
      level="beginner", family="russian_twist",
      contra=["herniated_disc", "lower_back_pain"],
      cue="Rotate the ribs, not just the arms, and keep the chest tall.",
      easier="keep the heels on the floor",
      harder="Russian Twist holding a weight"),

    M("Ab Wheel Rollout", src="Barbell Ab Rollout - On Knees", bucket="core",
      pattern="anti_extension", mechanic="compound", equipment="other",
      role="accessory", skill_floor="advanced", level="advanced",
      family="rollout", contra=["lower_back_pain", "herniated_disc"],
      instructions=[
          "Kneel on a mat and hold the wheel handles under the shoulders, arms straight.",
          "Brace the trunk and tuck the pelvis so the low back is flat, not arched.",
          "Roll the wheel forward only as far as you can hold that flat back position.",
          "Pull through the abdominals to draw the wheel back to the starting position.",
          "If the low back arches at any point, shorten the range — that distance is your working range.",
      ],
      cue="Only roll as far as you can keep the low back flat. That distance is your range."),

    M("Hollow Body Hold", src=None, bucket="core", pattern="anti_extension",
      mechanic="isolation", equipment="bodyweight", role="accessory",
      skill_floor="intermediate", level="intermediate", family="hollow_hold",
      rep_style="isometric", pm=["abdominals"], sm=["hip flexors"],
      instructions=[
          "Lie on your back with the arms overhead and the legs straight.",
          "Press the low back firmly into the floor and hold it there.",
          "Lift the shoulders and legs a few inches, keeping the back flat.",
          "Hold, breathing shallowly, and stop the moment the low back lifts away.",
      ],
      cue="If the low back comes off the floor, bend the knees — do not just endure it.",
      easier="Dead Bug",
      harder="Hollow Body Hold with the arms overhead"),

    M("Leg Raise on Parallel Bars", src="Leg Pull-In", bucket="core",
      pattern="anti_extension", mechanic="isolation", equipment="bodyweight",
      role="accessory", skill_floor="intermediate", level="intermediate",
      family="leg_raise",
      cue="Support your weight on the forearms and lift with the abs, not a swing.",
      easier="Lying Leg Raise",
      harder="Hanging Leg Raise"),
]

FILL_CONDITIONING = [
    M("Air Bike", src="Air Bike (Assault Bike)", bucket="cardio",
      pattern="locomotion", mechanic="compound", equipment="air_bike",
      role="finisher", skill_floor="intermediate", level="intermediate",
      rep_style="time", category="cardio", family="air_bike", impact="none",
      contra=["hypertension", "heart_disease"], cal_per_min=14,
      cue="Brutal and completely self-limiting — you can only go as hard as you can."),

    M("Battle Ropes", bucket="cardio", pattern="locomotion", mechanic="compound",
      equipment="battle_ropes", role="finisher", skill_floor="intermediate",
      level="intermediate", rep_style="time", category="cardio",
      family="battle_rope", impact="none",
      contra=["hypertension", "heart_disease", "shoulder_injury"], cal_per_min=12,
      cue="Stay in a quarter squat and let the arms work independently."),

    M("Sprint Intervals (HIIT)", bucket="cardio", pattern="locomotion",
      mechanic="compound", equipment="bodyweight", role="finisher",
      skill_floor="advanced", level="advanced", rep_style="time",
      category="cardio", family="sprint", impact="high",
      contra=["hypertension", "heart_disease", "bad_knee", "knee_replacement"],
      cal_per_min=15,
      cue="Maximal effort by definition. If you can hold a conversation it is not this."),

    M("HIIT Circuit", bucket="cardio", pattern="locomotion", mechanic="compound",
      equipment="bodyweight", role="finisher", skill_floor="intermediate",
      level="intermediate", rep_style="time", category="cardio",
      family="hiit_circuit", impact="high",
      contra=["hypertension", "heart_disease", "bad_knee"], cal_per_min=13,
      cue="Rest is part of the prescription — cutting it short makes it easier, not harder."),

    M("Incline Treadmill Walk", src=None, bucket="cardio", pattern="locomotion",
      mechanic="compound", equipment="treadmill", role="finisher",
      skill_floor="beginner", level="beginner", rep_style="time",
      category="cardio", family="walk", impact="low", cal_per_min=7,
      pm=["cardiovascular system"], sm=["glutes", "calves"],
      instructions=[
          "Set the treadmill to a walking pace you could hold a conversation at.",
          "Raise the incline until the effort feels moderate but sustainable.",
          "Walk tall without holding the handrails, letting the arms swing naturally.",
          "Lower the incline for the last two minutes to bring the heart rate down.",
      ],
      cue="The incline does the work, not the speed. Hands off the rails."),
]

FILL = (FILL_CHEST + FILL_BACK + FILL_SHOULDERS + FILL_ARMS + FILL_LEGS
        + FILL_CORE + FILL_CONDITIONING)
