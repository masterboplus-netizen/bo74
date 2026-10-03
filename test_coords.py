from core.measures import get_walls_ordered
from core.geometry import calc_wall_coords

w = get_walls_ordered(64)
print(f"walls count: {len(w)}")
for x in w:
    print(f"  {x.get('wall_pos')} | len={x.get('length')} | angle={x.get('angle_value')} | order={x.get('order_num')}")

print("=== calc_wall_coords ===")
coords = calc_wall_coords(w)
print(f"coords count: {len(coords)}")
for c in coords:
    print(f"  {c.get('wall_pos')}: ({c.get('start_x')},{c.get('start_y')}) -> ({c.get('end_x')},{c.get('end_y')}) len={c.get('length')}")
