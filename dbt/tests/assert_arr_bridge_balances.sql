-- Fails if opening + new + reactivation + expansion - contraction - churn != closing ARR.
select *
from {{ ref('mart_arr_bridge') }}
where abs(opening_arr + new_arr + reactivation_arr + expansion_arr
          - contraction_arr - churned_arr - closing_arr) > 0.01
