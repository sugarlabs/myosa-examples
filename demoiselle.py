#! /usr/bin/env python
#
# demoiselle.py Standalone version of DemoiselleActivity.py
# Copyright (C) 2010  James D. Simmons
# Adapted from code in the article "Rapid Game Development In
# Python" by Richard Jones.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
#

import pygame, math, sys
from pygame.locals import *
screen = pygame.display.set_mode((1024, 768))
background = pygame.image.load('sky.jpg')
screen.blit(background, (0,0))
clock = pygame.time.Clock()
class AirplaneSprite(pygame.sprite.Sprite):
    MAX_FORWARD_SPEED = 10
    MIN_FORWARD_SPEED = 1
    ACCELERATION = 2
    TURN_SPEED = 5
    def __init__(self, image, position):
        pygame.sprite.Sprite.__init__(self)
        self.src_image = pygame.image.load(image)
        self.rect = pygame.Rect(self.src_image.get_rect())
        self.position = position
        self.rect.center = self.position
        self.speed = 1
        self.direction = 0
        self.k_left = self.k_right = self.k_down = self.k_up = 0
    def update(self, deltat):
        # SIMULATION
        self.speed += (self.k_up + self.k_down)
        if self.speed > self.MAX_FORWARD_SPEED:
            self.speed = self.MAX_FORWARD_SPEED
        if self.speed < self.MIN_FORWARD_SPEED:
            self.speed = self.MIN_FORWARD_SPEED
        self.direction += (self.k_right + self.k_left)
        x, y = self.position
        rad = self.direction * math.pi / 180
        x += -self.speed * math.cos(rad)
        y += -self.speed * math.sin(rad)
        if y < 0:
            y = 768
            
        if x < 0:
            x = 1024
            
        if x > 1024:
            x = 0
            
        if y > 768:
            y = 0
        self.position = (x, y)
        self.image = pygame.transform.rotate(self.src_image, -self.direction)
        self.rect = self.image.get_rect()
        self.rect.center = self.position

class PadSprite(pygame.sprite.Sprite):
    def __init__(self, position):
        pygame.sprite.Sprite.__init__(self)
        self.normal = pygame.image.load('pad_normal.png')
        self.rect = pygame.Rect(self.normal.get_rect())
        self.rect.center = position
        self.image = self.normal
        self.hit = pygame.image.load('pad_hit.png')
    def update(self, hit_list):
        if self in hit_list: 
            self.image = self.hit
        else: 
            self.image = self.normal

pads = [
    PadSprite((200, 200)),
    PadSprite((800, 200)),
    PadSprite((200, 600)),
    PadSprite((800, 600)),
]
pad_group = pygame.sprite.RenderPlain(*pads)

# CREATE AN AIRPLANE AND RUN
rect = screen.get_rect()
airplane = AirplaneSprite('demoiselle.png', rect.center)
airplane_sprite = pygame.sprite.RenderPlain(airplane)
while 1:
    # USER INPUT
    deltat = clock.tick(30)
    for event in pygame.event.get():
        if not hasattr(event, 'key'): continue
        down = event.type == KEYDOWN
        if event.key == K_RIGHT: 
            airplane.k_right = down * -5
        elif event.key == K_LEFT: 
            airplane.k_left = down * 5
        elif event.key == K_UP: 
            airplane.k_up = down * 2
        elif event.key == K_DOWN: 
            airplane.k_down = down * -2
        elif event.key == K_ESCAPE: 
            sys.exit(0)
    # RENDERING
    pad_group.clear(screen, background)
    airplane_sprite.clear(screen, background)
    collisions = pygame.sprite.spritecollide(airplane, pad_group,  False)
    pad_group.update(collisions)
    pad_group.draw(screen)
    airplane_sprite.update(deltat)
    airplane_sprite.draw(screen)
    pygame.display.flip()
