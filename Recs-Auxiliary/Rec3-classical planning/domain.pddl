(define (domain blocks)
  (:requirements :strips :typing)
  (:types block)

  (:predicates
    (on ?x - block ?y - block)
    (ontable ?x - block)
    (clear ?x - block)
    (holding ?x - block)
    (handempty)
  )

  ;; PICKUP(x): pick a clear block up from the table
  (:action pickup
    :parameters (?x - block)
    :precondition (and (ontable ?x) (clear ?x) (handempty))
    :effect (and
      (holding ?x)
      (not (ontable ?x))
      (not (clear ?x))
      (not (handempty))
    )
  )

  ;; PUTDOWN(x): put a held block down onto the table
  (:action putdown
    :parameters (?x - block)
    :precondition (holding ?x)
    :effect (and
      (ontable ?x) (clear ?x) (handempty)
      (not (holding ?x))
    )
  )

  ;; UNSTACK(x, y): lift a clear block x off the top of y
  (:action unstack
    :parameters (?x - block ?y - block)
    :precondition (and (on ?x ?y) (clear ?x) (handempty))
    :effect (and
      (holding ?x) (clear ?y)
      (not (on ?x ?y))
      (not (clear ?x))
      (not (handempty))
    )
  )

  ;; STACK(x, y): place a held block x onto a clear block y
  (:action stack
    :parameters (?x - block ?y - block)
    :precondition (and (holding ?x) (clear ?y))
    :effect (and
      (on ?x ?y) (handempty) (clear ?x)
      (not (holding ?x))
      (not (clear ?y))
    )
  )
)
