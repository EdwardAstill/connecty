"""fiber analysis/strain compatability method
Method to determine the position of the neutral axis

1. set up a grid of cells / points that represent the plate
2. pick an angle theta parallel to the resultant moment (is it perpendicular or parallel to resultant moment)
2. draw a neutral axis
3. determine the strain in each cell
    cells "below"(on the side that does not contain the origin) the neutral axis  will have a negative strain (compression)
    cells "above" the neutral axis  will have a positive strain (tension)
    if there are no bolt cells "above" the neutral axis then an error should be returned because the plate cannot resist the moment
    the strain in the "below" cells is determined by the distance from the neutral axis
    the strain in the "above/bolt" cells is determined by the distance from the neutral axis
    the strain in the above/bolt cells is scaled so that the moment about the given neutral axis created by the strains is equal in magnitude to the moment created by the below cells
4. scale the forces so ...



"""

