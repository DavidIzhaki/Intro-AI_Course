(define (problem blocks-3)
  (:domain blocks)
  (:objects A B C - block)

  (:init
    (on C A) (ontable A) (ontable B)
    (clear C) (clear B) (handempty)
  )

  (:goal (and (on A B) (on B C) (ontable C)))
)