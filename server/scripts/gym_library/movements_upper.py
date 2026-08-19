"""Curated upper-body movements.

`src` names the upstream free-exercise-db entry whose instructions and anatomy
are reused. Where it is None the entry is written here, because the movement a
coach would actually reach for was missing from the import — a plain push-up and
a knee push-up among them, in a library holding 141 bodyweight exercises.
"""

from .spec import M

CHEST = [
    # ---- bodyweight: the progression a home user actually climbs -----------
    M("Knee Push-Up", src=None, bucket="chest", pattern="push_h",
      mechanic="compound", equipment="bodyweight", role="main",
      skill_floor="beginner", level="beginner", family="push_up",
      pm=["chest"], sm=["triceps", "shoulders"],
      instructions=[
          "Kneel on a mat and place your hands slightly wider than your shoulders, fingers spread.",
          "Walk your knees back until your body forms a straight line from head to knees.",
          "Brace your trunk, then bend the elbows to lower your chest toward the floor.",
          "Keep the elbows angled about 45 degrees from your body rather than flared wide.",
          "Press the floor away until the arms are straight, without letting the hips sag or pike.",
      ],
      cue="Squeeze the glutes — it stops the low back sagging and makes the trunk do its job.",
      easier="Incline Push-Up against a wall", harder="Incline Push-Up on a bench"),

    M("Incline Push-Up", bucket="chest", pattern="push_h", mechanic="compound",
      equipment="bodyweight", role="main", skill_floor="beginner",
      level="beginner", family="push_up",
      cue="The higher the surface, the easier it is — lower it as you get stronger.",
      easier="Knee Push-Up", harder="Push-Up"),

    M("Push-Up", src="Pushups", canonical=True, bucket="chest", pattern="push_h",
      mechanic="compound", equipment="bodyweight", role="main",
      skill_floor="intermediate", level="beginner", family="push_up",
      instructions=[
          "Lie face down and place the hands slightly wider than the shoulders, level with the mid-chest.",
          "Tuck the toes under and press up until the arms are straight and the body is one line from head to heels.",
          "Lower under control until the chest is a few centimetres off the floor, elbows angled about 45 degrees from the ribs.",
          "Press the floor away to return to straight arms without letting the hips sag or pike.",
          "Keep the neck long — look at a spot on the floor slightly ahead of the hands.",
      ],
      cue="One line from ear to ankle; the hips move with the chest, not before it.",
      easier="Incline Push-Up", harder="Decline Push-Up"),

    M("Decline Push-Up", src="Decline Push-Up", bucket="chest", pattern="push_h",
      mechanic="compound", equipment="bodyweight", role="accessory",
      skill_floor="intermediate", level="intermediate", family="push_up",
      instructions=[
          "Set the feet on a bench or step and place the hands slightly wider than the shoulders on the floor.",
          "Press up until the arms are straight and the body forms one line from head to heels.",
          "Lower the chest toward the floor under control, keeping the elbows angled back rather than flared.",
          "Press back to straight arms, keeping the hips from sagging.",
          "The higher the feet, the more the load shifts to the upper chest and shoulders.",
      ],
      cue="Feet elevated shifts the load toward the upper chest and shoulders.",
      easier="Push-Up",
      harder="Pike Push-Up"),

    M("Close-Grip Push-Up", src="Push-Ups - Close Triceps Position",
      bucket="triceps", pattern="push_h", mechanic="compound",
      equipment="bodyweight", role="accessory", skill_floor="intermediate",
      level="intermediate", family="push_up",
      cue="Elbows stay close to the ribs — that is what moves the work to the triceps.",
      easier="Incline Close-Grip Push-Up",
      harder="Diamond Push-Up"),

    M("Chest Dip", src="Dips - Chest Version", bucket="chest", pattern="push_v",
      mechanic="compound", equipment="bodyweight", role="accessory",
      skill_floor="intermediate", level="intermediate", family="dip",
      contra=["shoulder_injury", "rotator_cuff"],
      cue="Lean the torso forward about 30 degrees; upright turns it into a triceps movement.",
      easier="Bench Dips"),

    # ---- dumbbell ----------------------------------------------------------
    M("Dumbbell Bench Press", canonical=True, bucket="chest", pattern="push_h",
      mechanic="compound", equipment="dumbbell", role="main",
      load_class="bench_press", skill_floor="beginner", level="beginner",
      family="bench_press",
      cue="Wrists stacked over the elbows; the dumbbells travel over the mid-chest, not the throat."),

    M("Incline Dumbbell Press", bucket="chest", pattern="push_h",
      mechanic="compound", equipment="dumbbell", role="accessory",
      load_class="incline_press", skill_floor="beginner", level="beginner",
      family="incline_press",
      cue="Thirty degrees is enough — steeper and the front delt takes the set."),

    M("Dumbbell Floor Press", bucket="chest", pattern="push_h",
      mechanic="compound", equipment="dumbbell", role="accessory",
      load_class="floor_press", skill_floor="beginner", level="beginner",
      family="floor_press",
      cue="The floor caps the range, which is why this is the pressing option for a cranky shoulder."),

    M("Dumbbell Flyes", bucket="chest", pattern="isolation", mechanic="isolation",
      equipment="dumbbell", role="accessory", load_class="fly",
      skill_floor="intermediate", level="intermediate", family="fly",
      cue="A wide arc with soft elbows. If you can press it, it is too heavy for a fly."),

    # ---- barbell -----------------------------------------------------------
    M("Barbell Bench Press", src="Barbell Bench Press - Medium Grip",
      canonical=True, bucket="chest", pattern="push_h", mechanic="compound", equipment="barbell",
      role="main", load_class="bench_press", skill_floor="beginner",
      level="beginner", family="bench_press",
      cue="Shoulder blades pinched and down into the bench before the bar leaves the rack.",
      harder="Barbell Bench Press with a pause on the chest"),

    M("Incline Barbell Bench Press", src="Barbell Incline Bench Press - Medium Grip",
      bucket="chest", pattern="push_h", mechanic="compound", equipment="barbell",
      role="accessory", load_class="incline_press", skill_floor="intermediate",
      level="intermediate", family="incline_press",
      cue="Bar touches high on the chest, just under the collarbone."),

    # ---- machine / cable ---------------------------------------------------
    M("Machine Bench Press", src="Machine Bench Press", bucket="chest",
      pattern="push_h", mechanic="compound", equipment="machine", role="main",
      load_class="bench_press", skill_floor="beginner", level="beginner",
      family="bench_press",
      cue="Set the seat so the handles sit at mid-chest height."),

    M("Cable Crossover", bucket="chest", pattern="isolation", mechanic="isolation",
      equipment="cable", role="accessory", load_class="fly",
      skill_floor="intermediate", level="intermediate", family="fly",
      cue="Finish with the hands together and the chest squeezed, not the arms locked."),

    M("Pec Deck", src="Butterfly", bucket="chest", pattern="isolation",
      mechanic="isolation", equipment="machine", role="accessory",
      load_class="fly", skill_floor="beginner", level="beginner", family="fly",
      cue="Elbows level with the shoulders; drop them and it becomes a press."),
]

BACK = [
    # ---- bodyweight: the hole the import left ------------------------------
    M("Inverted Row", src=None, bucket="back", pattern="pull_h",
      mechanic="compound", equipment="bodyweight", role="main",
      skill_floor="beginner", level="beginner", family="bodyweight_row",
      pm=["middle back"], sm=["lats", "biceps", "shoulders"],
      instructions=[
          "Set a bar at roughly hip height in a rack, or use the edge of a sturdy table.",
          "Lie underneath it and take an overhand grip a little wider than your shoulders.",
          "Walk the feet out until the body is straight and the arms are fully extended.",
          "Pull the chest to the bar by driving the elbows down and back, keeping the hips level.",
          "Pause when the chest touches, then lower under control to full arm extension.",
      ],
      cue="The more horizontal your body, the harder it is. Walk the feet in to make it easier.",
      easier="Inverted Row with the bar set higher", harder="Inverted Row with feet elevated"),

    M("Superman Hold", bucket="back", pattern="isolation", mechanic="isolation",
      equipment="bodyweight", role="accessory", skill_floor="beginner",
      level="beginner", family="back_extension", rep_style="isometric",
      contra=["lower_back_pain", "herniated_disc"],
      cue="Lift by lengthening, not by cranking the low back — think long, not high.",
      easier="lift only the arms, keeping the legs down",
      harder="Superman Hold with a longer hold"),

    M("Prone Swimmer", bucket="back", pattern="isolation", mechanic="isolation",
      equipment="bodyweight", role="accessory", skill_floor="beginner",
      level="beginner", family="prone_raise",
      cue="Small movement, slow tempo. This is upper-back endurance work, not a lift.",
      harder="Prone Y-Raise"),

    M("Wall Angel Row", bucket="back", pattern="pull_h", mechanic="isolation",
      equipment="bodyweight", role="accessory", skill_floor="beginner",
      level="beginner", family="wall_angel",
      cue="Keep the low back flat against the wall; if it arches, you have gone too far.",
      harder="Band Row"),

    M("Pull-Up", src="Pullups", canonical=True, bucket="back", pattern="pull_v",
      mechanic="compound", equipment="bodyweight", role="main",
      skill_floor="intermediate", level="intermediate", family="pull_up",
      cue="Chest to the bar, shoulders away from the ears at the top.",
      easier="Inverted Row, then band-assisted pull-ups"),

    M("Chin-Up", bucket="back", pattern="pull_v", mechanic="compound",
      equipment="bodyweight", role="main", skill_floor="intermediate",
      level="intermediate", family="pull_up",
      cue="Underhand grip brings the biceps in, which is why it is the easier of the two.",
      easier="Inverted Row, then band-assisted chin-ups"),

    # ---- dumbbell ----------------------------------------------------------
    M("One-Arm Dumbbell Row", canonical=True, bucket="back", pattern="pull_h",
      mechanic="compound", equipment="dumbbell", role="main",
      load_class="chest_supported_row", skill_floor="beginner",
      level="beginner", family="db_row", unilateral=True,
      cue="Row to the hip, not the shoulder, and keep the torso square to the floor."),

    M("Bent Over Two-Dumbbell Row", bucket="back", pattern="pull_h",
      mechanic="compound", equipment="dumbbell", role="accessory",
      load_class="barbell_row", skill_floor="intermediate", level="intermediate",
      family="db_row", contra=["lower_back_pain", "herniated_disc"],
      cue="Hinge to about 45 degrees and hold it — the back angle should not change as you row."),

    M("Dumbbell Shrug", bucket="back", pattern="isolation", mechanic="isolation",
      equipment="dumbbell", role="accessory", load_class="shrug",
      skill_floor="beginner", level="intermediate", family="shrug",
      cue="Straight up and down. Rolling the shoulders adds nothing but wear."),

    # ---- barbell -----------------------------------------------------------
    M("Bent Over Barbell Row", canonical=True, bucket="back", pattern="pull_h",
      mechanic="compound", equipment="barbell", role="main",
      load_class="barbell_row", skill_floor="beginner", level="intermediate",
      family="barbell_row", contra=["lower_back_pain", "herniated_disc"],
      cue="Bar to the belly button. If the torso rises to meet it, the weight is winning."),

    M("Barbell Shrug", bucket="back", pattern="isolation", mechanic="isolation",
      equipment="barbell", role="accessory", load_class="shrug",
      skill_floor="beginner", level="intermediate", family="shrug",
      cue="Pause at the top for a second — traps respond to the hold, not the bounce."),

    # ---- machine / cable ---------------------------------------------------
    M("Wide-Grip Lat Pulldown", src="Wide-Grip Lat Pulldown", canonical=True, bucket="back",
      pattern="pull_v", mechanic="compound", equipment="machine", role="main",
      load_class="pulldown", skill_floor="beginner", level="beginner",
      family="pulldown",
      cue="Pull the bar to the collarbone by driving the elbows down, not by leaning back."),

    M("V-Bar Pulldown", bucket="back", pattern="pull_v", mechanic="compound",
      equipment="machine", role="accessory", load_class="pulldown",
      skill_floor="beginner", level="beginner", family="pulldown",
      cue="The close neutral grip is kinder to the shoulder than a wide bar."),

    M("Seated Cable Row", src="Seated Cable Rows", canonical=True, bucket="back",
      pattern="pull_h", mechanic="compound", equipment="cable", role="main",
      load_class="seated_row", skill_floor="beginner", level="beginner",
      family="cable_row",
      cue="Sit tall and let the shoulder blades travel — do not row with a locked upper back."),

    M("Face Pull", bucket="shoulders", pattern="pull_h", mechanic="isolation",
      equipment="cable", role="accessory", load_class="face_pull",
      skill_floor="beginner", level="beginner", family="face_pull",
      instructions=[
          "Set a rope attachment on a cable pulley at roughly face height and take an end in each hand.",
          "Step back until the arms are extended and there is tension on the cable, thumbs pointing back.",
          "Pull the rope toward your forehead, driving the elbows high and wide and separating the hands.",
          "Pause briefly with the hands beside the ears and the shoulder blades squeezed together.",
          "Return to full arm extension under control, letting the shoulder blades travel forward.",
      ],
      cue="Rope to the forehead, elbows high. This is the movement that keeps pressing pain-free."),

    M("Straight-Arm Pulldown", bucket="back", pattern="pull_v",
      mechanic="isolation", equipment="cable", role="accessory",
      load_class="straight_arm_pulldown", skill_floor="intermediate",
      level="intermediate", family="pullover",
      cue="Arms stay long. The moment the elbows bend it becomes a pushdown."),
]

SHOULDERS = [
    M("Pike Push-Up", src=None, bucket="shoulders",
      pattern="push_v", mechanic="compound", equipment="bodyweight",
      role="main", skill_floor="intermediate", level="intermediate",
      family="overhead_press", pm=["shoulders"], sm=["triceps", "chest"],
      instructions=[
          "Start in a push-up position and walk the feet in until the hips are high and the body forms an inverted V.",
          "Set the hands slightly wider than the shoulders with the fingers spread.",
          "Bend the elbows to lower the crown of the head toward the floor between the hands.",
          "Keep the hips high throughout — letting them drop turns this back into a push-up.",
          "Press back to the starting position until the arms are straight.",
      ],
      cue="Feet closer to the hands means more of your weight overhead, which is the progression.",
      easier="Incline Push-Up", harder="Pike Push-Up with the feet on a box"),

    M("Dumbbell Shoulder Press", canonical=True, bucket="shoulders", pattern="push_v",
      mechanic="compound", equipment="dumbbell", role="main",
      load_class="overhead_press", skill_floor="beginner", level="beginner",
      family="overhead_press", contra=["shoulder_injury"],
      cue="Ribs down, glutes tight — the press should not turn into a standing backbend."),

    M("Arnold Dumbbell Press", bucket="shoulders", pattern="push_v",
      mechanic="compound", equipment="dumbbell", role="accessory",
      load_class="overhead_press", skill_floor="intermediate",
      level="intermediate", family="overhead_press",
      contra=["shoulder_injury", "rotator_cuff"],
      cue="Rotate as you press, and go lighter than a straight press — the rotation costs you."),

    M("Barbell Shoulder Press", canonical=True, bucket="shoulders", pattern="push_v",
      mechanic="compound", equipment="barbell", role="main",
      load_class="overhead_press", skill_floor="beginner", level="intermediate",
      family="overhead_press", contra=["shoulder_injury", "hypertension"],
      cue="Head moves back to let the bar pass, then through as it locks out overhead."),

    M("Side Lateral Raise", bucket="shoulders", pattern="isolation",
      mechanic="isolation", equipment="dumbbell", role="accessory",
      load_class="lateral_raise", skill_floor="beginner", level="beginner",
      family="lateral_raise",
      cue="Lead with the elbows to shoulder height. Light weight — this is a small muscle."),

    M("Front Dumbbell Raise", bucket="shoulders", pattern="isolation",
      mechanic="isolation", equipment="dumbbell", role="accessory",
      load_class="front_raise", skill_floor="beginner", level="beginner",
      family="front_raise",
      cue="Stop at shoulder height and resist the swing on the way down."),

    M("Bent Over Rear Delt Raise", src="Bent Over Dumbbell Rear Delt Raise With Head On Bench",
      bucket="shoulders", pattern="isolation", mechanic="isolation",
      equipment="dumbbell", role="accessory", load_class="rear_delt",
      skill_floor="beginner", level="beginner", family="rear_delt",
      cue="Think of pulling the dumbbells apart rather than lifting them up."),

    M("External Rotation", bucket="shoulders", pattern="rotation",
      mechanic="isolation", equipment="dumbbell", role="warmup",
      load_class="external_rotation", skill_floor="beginner", level="beginner",
      family="external_rotation",
      cue="Elbow pinned to the ribs. Two to five kilos is the whole range here — this is a cuff drill, not a lift."),

    M("Band Pull Apart", bucket="shoulders", pattern="pull_h",
      mechanic="isolation", equipment="bands", role="warmup",
      skill_floor="beginner", level="beginner", family="pull_apart",
      cue="Arms long, squeeze the shoulder blades. Best thing you can do before pressing."),

    M("Upright Row", src=None, bucket="shoulders", pattern="pull_v",
      mechanic="compound", equipment="barbell", role="accessory",
      load_class="upright_row", skill_floor="intermediate", level="intermediate",
      family="upright_row", contra=["shoulder_injury", "rotator_cuff"],
      pm=["shoulders"], sm=["traps", "biceps"],
      instructions=[
          "Stand holding a barbell at arm's length with an overhand grip about shoulder-width apart.",
          "Keep the bar close to the body and lead with the elbows as you pull it upward.",
          "Stop when the upper arms reach shoulder height — no higher.",
          "Pause briefly, then lower the bar under control to full arm extension.",
      ],
      cue="Stop at shoulder height. Pulling to the chin is where shoulders get pinched."),
]

ARMS = [
    M("Barbell Curl", bucket="biceps", pattern="isolation", mechanic="isolation",
      equipment="barbell", role="accessory", load_class="curl",
      skill_floor="beginner", level="beginner", family="curl",
      cue="Elbows stay at your sides. If they drift forward, the shoulders are helping."),

    M("Dumbbell Bicep Curl", src="Dumbbell Bicep Curl", bucket="biceps",
      pattern="isolation", mechanic="isolation", equipment="dumbbell",
      role="accessory", load_class="curl", skill_floor="beginner",
      level="beginner", family="curl",
      cue="Supinate as you lift — turning the palm up is half the movement."),

    M("Hammer Curls", bucket="biceps", pattern="isolation", mechanic="isolation",
      equipment="dumbbell", role="accessory", load_class="hammer_curl",
      skill_floor="beginner", level="beginner", family="hammer_curl",
      cue="Neutral grip throughout; this one builds the forearm as much as the biceps."),

    M("Preacher Curl", bucket="biceps", pattern="isolation", mechanic="isolation",
      equipment="barbell", role="accessory", load_class="preacher_curl",
      skill_floor="intermediate", level="intermediate", family="curl",
      contra=["elbow_injury"],
      cue="Do not slam into full extension at the bottom — the elbow does not enjoy it."),

    M("Self-Resisted Biceps Curl", bucket="biceps", pattern="isolation",
      mechanic="isolation", equipment="bodyweight", role="accessory",
      skill_floor="beginner", level="beginner", family="curl",
      cue="Push down with the free hand hard enough that the last rep is a fight.",
      harder="Towel Biceps Curl"),

    M("Triceps Pushdown", src="Triceps Pushdown", bucket="triceps",
      pattern="isolation", mechanic="isolation", equipment="cable",
      role="accessory", load_class="triceps_pushdown", skill_floor="beginner",
      level="beginner", family="pushdown",
      cue="Elbows locked to the ribs; only the forearms move."),

    M("Lying Triceps Press", bucket="triceps", pattern="isolation",
      mechanic="isolation", equipment="barbell", role="accessory",
      load_class="skullcrusher", skill_floor="intermediate", level="intermediate",
      family="triceps_extension", contra=["elbow_injury"],
      cue="Lower to the forehead or just behind it, and keep the upper arms still."),

    M("Standing Dumbbell Triceps Extension", bucket="triceps", pattern="isolation",
      mechanic="isolation", equipment="dumbbell", role="accessory",
      load_class="triceps_extension", skill_floor="beginner", level="beginner",
      family="triceps_extension", contra=["shoulder_injury"],
      cue="Elbows point at the ceiling and stay there."),

    M("Bench Dips", bucket="triceps", pattern="push_v", mechanic="compound",
      equipment="bodyweight", role="accessory", skill_floor="beginner",
      level="beginner", family="dip", contra=["shoulder_injury", "rotator_cuff"],
      cue="Keep the hips close to the bench — drifting away is what strains the shoulder.",
      easier="bend the knees and keep the feet close",
      harder="Chest Dip"),
]
