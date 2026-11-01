import math

import numpy as np
import pygame


def border_distance(mask, step, reach):
    if not mask.any():return np.full(mask.shape,-reach,dtype=np.float32)
    if mask.all():return np.full(mask.shape,reach,dtype=np.float32)
    distances=[]
    for region in (mask,~mask):
        distance=np.where(region,reach,0).astype(np.float32)
        for _ in range(math.ceil(reach/step)):
            padded=np.pad(distance,1,constant_values=reach)
            updated=distance.copy()
            for dy,dx,cost in ((0,1,step),(2,1,step),(1,0,step),(1,2,step),
                               (0,0,step*math.sqrt(2)),(0,2,step*math.sqrt(2)),
                               (2,0,step*math.sqrt(2)),(2,2,step*math.sqrt(2))):
                neighbor=padded[dy:dy+mask.shape[0],dx:dx+mask.shape[1]]
                np.minimum(updated,neighbor+cost,out=updated)
            distance=updated
        distances.append(distance)
    return np.where(mask,distances[0]-step*.5,step*.5-distances[1]).astype(np.float32)


def soften_opacity(values):
    values=values.astype(np.uint16)
    padded=np.pad(values,((0,0),(1,1)),mode='edge')
    horizontal=(padded[:,:-2]+padded[:,1:-1]*2+padded[:,2:]+2)>>2
    padded=np.pad(horizontal,((1,1),(0,0)),mode='edge')
    return ((padded[:-2]+padded[1:-1]*2+padded[2:]+2)>>2).astype(np.uint8)


def city_connected_mask(mask, positions, step):
    surface=pygame.Surface((mask.shape[1],mask.shape[0]),pygame.SRCALPHA)
    alpha=pygame.surfarray.pixels_alpha(surface)
    alpha[:]=mask.T.astype(np.uint8)*255
    del alpha
    source=pygame.mask.from_surface(surface)
    retained=pygame.mask.Mask(source.get_size())
    for x,y in positions:
        point=(min(mask.shape[1]-1,max(0,int(x//step))),min(mask.shape[0]-1,max(0,int(y//step))))
        if source.get_at(point) and not retained.get_at(point):
            retained.draw(source.connected_component(point),(0,0))
    image=retained.to_surface(setcolor=(255,255,255,255),unsetcolor=(0,0,0,0))
    return pygame.surfarray.array_alpha(image).T>0
