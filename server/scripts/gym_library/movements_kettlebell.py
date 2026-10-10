"""Kettlebell movements, for the practitioner whose only implement is a bell.

The library held one kettlebell movement — the swing — so someone who ticked
"kettlebell" on the gym form was given a bodyweight plan with swings appended
to every day, and the swing is an intermediate, ballistic hinge that opened
nothing. One bell covers the whole programme: a squat, a hinge, a press, a row,
a floor press and a carry. These are those six, written to the house style.

The clinical judgment of each mirrors its dumbbell analogue (see `clinical.py`),
because the joint positions are the same; where the bell changes something —
the rack position, a single implement held in two hands — the entry says so.
"""

from .spec import M

KETTLEBELL = [
    M("Kettlebell Goblet Squat", src=None, bucket="legs", pattern="squat",
      mechanic="compound", equipment="kettlebell", role="main",
      load_class="front_squat", skill_floor="beginner", level="beginner",
      family="squat", pm=["quadriceps"], sm=["glutes", "adductors", "core"],
      instructions=[
          "Hold the kettlebell by the horns at chest height, elbows pointing down.",
          "Stand with the feet a little wider than the hips and the toes turned slightly out.",
          "Sit down between the hips, keeping the chest up and the bell close to the body.",
          "Go as deep as you can while the heels stay down and the back stays long.",
          "Drive through the whole foot to stand, breathing out as you rise.",
      ],
      cue="The bell at the chest is a counterweight — let it keep you upright.",
      easier="Box Squat to a Chair", harder="Kettlebell Goblet Squat with a pause at the bottom"),

    M("Kettlebell Deadlift", src=None, bucket="legs", pattern="hinge",
      mechanic="compound", equipment="kettlebell", role="main",
      load_class="romanian_deadlift", skill_floor="beginner", level="beginner",
      family="kettlebell_deadlift", pm=["hamstrings"], sm=["glutes", "lower back", "forearms"],
      instructions=[
          "Stand with the kettlebell on the floor between the feet, in line with the ankles.",
          "Push the hips back, bend the knees a little and take the handle in both hands.",
          "Set the back flat and pull the shoulders down away from the ears.",
          "Stand up by driving the hips forward, keeping the bell close to the legs.",
          "Lower it the same way — hips back first — until it touches the floor lightly.",
      ],
      cue="Hips back, not knees forward. This is the hinge the swing is built on.",
      easier="Banded Romanian Deadlift", harder="Kettlebell Swing"),

    M("One-Arm Kettlebell Row", src=None, bucket="back", pattern="pull_h",
      mechanic="compound", equipment="kettlebell", role="main",
      load_class="chest_supported_row", skill_floor="beginner", level="beginner",
      family="db_row", unilateral=True, pm=["lats"], sm=["middle back", "biceps", "rear deltoids"],
      instructions=[
          "Place one hand and the same-side knee on a bench or sturdy chair, the other foot on the floor.",
          "Hold the kettlebell in the free hand with the arm hanging straight below the shoulder.",
          "Keep the back flat and the shoulders square to the floor.",
          "Pull the bell toward the hip, elbow close to the body, breathing out as you pull.",
          "Lower it until the arm is straight again, without letting the shoulder drop.",
      ],
      cue="Row to the hip, not the chest — the elbow travels back, not up."),

    M("Kettlebell Overhead Press", src=None, bucket="shoulders", pattern="push_v",
      mechanic="compound", equipment="kettlebell", role="main",
      load_class="overhead_press", skill_floor="beginner", level="beginner",
      family="overhead_press", unilateral=True, pm=["shoulders"], sm=["triceps", "core"],
      instructions=[
          "Hold the kettlebell in the rack position: handle in the palm, bell resting on the outside of the forearm, elbow tucked in.",
          "Stand tall with the glutes squeezed and the ribs pulled down.",
          "Press the bell straight up, turning the palm forward as the arm straightens.",
          "Finish with the bicep beside the ear and the wrist straight, breathing out on the press.",
          "Lower under control back to the rack, then change sides after the set.",
      ],
      cue="Ribs down — if the low back arches, the bell is too heavy.",
      easier="Band Overhead Press"),

    M("Kettlebell Floor Press", src=None, bucket="chest", pattern="push_h",
      mechanic="compound", equipment="kettlebell", role="accessory",
      load_class="floor_press", skill_floor="beginner", level="beginner",
      family="floor_press", unilateral=True, pm=["chest"], sm=["triceps", "shoulders"],
      instructions=[
          "Lie on your back with the knees bent and a kettlebell held in one hand, upper arm on the floor.",
          "Hold the handle diagonally across the palm with the bell resting on the back of the forearm.",
          "Press the bell straight up over the shoulder, keeping the wrist straight and breathing out.",
          "Lower until the upper arm touches the floor, pause, then press again.",
          "Finish the set before changing sides.",
      ],
      cue="The floor stops the elbow — the range a sore shoulder can keep."),

    M("Kettlebell Suitcase Carry", src=None, bucket="core", pattern="carry",
      mechanic="compound", equipment="kettlebell", role="accessory",
      load_class="suitcase_carry", skill_floor="beginner", level="beginner",
      family="carry", rep_style="distance", unilateral=True,
      pm=["core"], sm=["forearms", "glutes", "traps"],
      instructions=[
          "Stand the kettlebell on the floor beside one foot.",
          "Hinge at the hips to pick it up in one hand, keeping the chest up.",
          "Stand tall with the shoulders level and resist being pulled to one side.",
          "Walk in a straight line for the prescribed distance, then swap hands.",
      ],
      cue="Staying square against a load on one side is the whole exercise."),
]
