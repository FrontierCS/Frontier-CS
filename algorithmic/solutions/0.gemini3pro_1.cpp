/*
    Competitive Programming Solution for Pack the Polyominoes
    Strategy: First-Fit Decreasing heuristic with bitmask grid.
*/
#include <iostream>
#include <vector>
#include <algorithm>
#include <cmath>

using namespace std;

// Basic Point structure
struct Point {
    int x, y;
};

// Input Polyomino structure
struct Polyomino {
    int id;
    int k;
    vector<Point> cells;
};

// Represents one of the 8 isometric transforms of a piece
struct Transform {
    int R, F; // Rotation (0-3), Reflection (0-1)
    vector<Point> offsets; // Coordinates relative to the top-left of the bounding box
    int min_tx, min_ty;    // The top-left coordinate of the transformed shape in its local frame
                           // Used to calculate the translation (X, Y).
};

// Processed Piece with all transforms
struct Piece {
    int original_id;
    int k;
    vector<Transform> transforms;
};

// Output structure
struct Placement {
    int X, Y, R, F;
};

// Grid State
// We use a vector of rows, where each row is a vector of 64-bit integers.
int W_grid;
int num_chunks;

struct GridRow {
    vector<uint64_t> chunks;
    GridRow(int count) : chunks(count, 0) {}
};

vector<GridRow> grid;

// Ensure grid has enough rows
void ensure_height(int h) {
    if (h >= (int)grid.size()) {
        // Reserve to avoid frequent reallocations if possible, though h grows slowly
        if (grid.capacity() <= h) grid.reserve(max(h + 1, (int)grid.size() * 2));
        while ((int)grid.size() <= h) {
            grid.emplace_back(num_chunks);
        }
    }
}

// Check if cell (r, c) is occupied
inline bool is_occupied(int r, int c) {
    if (r >= (int)grid.size()) return false;
    return (grid[r].chunks[c >> 6] >> (c & 63)) & 1;
}

// Set cell (r, c) as occupied
inline void set_occupied(int r, int c) {
    ensure_height(r);
    grid[r].chunks[c >> 6] |= (1ULL << (c & 63));
}

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    if (!(cin >> n)) return 0;

    vector<Polyomino> input_polys(n);
    long long total_cells = 0;
    for (int i = 0; i < n; ++i) {
        input_polys[i].id = i;
        cin >> input_polys[i].k;
        total_cells += input_polys[i].k;
        input_polys[i].cells.resize(input_polys[i].k);
        for (int j = 0; j < input_polys[i].k; ++j) {
            cin >> input_polys[i].cells[j].x >> input_polys[i].cells[j].y;
        }
    }

    // Heuristic: Set target width to ceil(sqrt(total_area)).
    // This encourages a square shape.
    int target_W = static_cast<int>(ceil(sqrt(total_cells)));
    // Constraint: Piece size at most 10. Width must be at least 10 to fit any piece.
    target_W = max(target_W, 10);
    
    W_grid = target_W;
    num_chunks = (W_grid + 63) / 64;
    
    // Precompute transforms
    vector<Piece> pieces(n);
    for (int i = 0; i < n; ++i) {
        pieces[i].original_id = input_polys[i].id;
        pieces[i].k = input_polys[i].k;
        pieces[i].transforms.resize(8);

        for (int F = 0; F <= 1; ++F) {
            for (int R = 0; R <= 3; ++R) {
                int idx = F * 4 + R;
                pieces[i].transforms[idx].R = R;
                pieces[i].transforms[idx].F = F;
                
                int min_x = 1000000, min_y = 1000000;
                vector<Point> t_cells(input_polys[i].k);

                for (int k = 0; k < input_polys[i].k; ++k) {
                    int x = input_polys[i].cells[k].x;
                    int y = input_polys[i].cells[k].y;
                    
                    // Apply Reflection
                    if (F) x = -x;
                    
                    // Apply Rotation
                    int rx, ry;
                    switch(R) {
                        case 0: rx = x; ry = y; break;
                        case 1: rx = y; ry = -x; break;
                        case 2: rx = -x; ry = -y; break;
                        case 3: rx = -y; ry = x; break;
                    }
                    
                    t_cells[k] = {rx, ry};
                    if (ry < min_y || (ry == min_y && rx < min_x)) {
                        min_y = ry;
                        min_x = rx;
                    }
                }
                
                pieces[i].transforms[idx].min_tx = min_x;
                pieces[i].transforms[idx].min_ty = min_y;
                
                pieces[i].transforms[idx].offsets.resize(input_polys[i].k);
                for(int k = 0; k < input_polys[i].k; ++k) {
                    pieces[i].transforms[idx].offsets[k].x = t_cells[k].x - min_x;
                    pieces[i].transforms[idx].offsets[k].y = t_cells[k].y - min_y;
                }
            }
        }
    }

    // Sort pieces by size descending
    vector<int> p_indices(n);
    for(int i=0; i<n; ++i) p_indices[i] = i;
    sort(p_indices.begin(), p_indices.end(), [&](int a, int b) {
        return pieces[a].k > pieces[b].k;
    });

    vector<Placement> results(n);
    int max_occupied_y = -1;
    int max_occupied_x = 0;
    int first_row_with_holes = 0;

    // Search parameter to prevent TLE on large inputs
    const int MAX_SEARCH_STEPS = 2000; 

    for (int i : p_indices) {
        const Piece& P = pieces[i];
        bool placed = false;
        
        int r = first_row_with_holes;
        int search_count = 0;
        
        while (!placed) {
            ensure_height(r);
            
            // Check if row is completely full to skip efficiently
            bool row_full = true;
            for (int c_chk = 0; c_chk < num_chunks; ++c_chk) {
                uint64_t mask = ~0ULL;
                if (c_chk == num_chunks - 1) {
                    int rem = W_grid % 64;
                    if (rem != 0) mask = (1ULL << rem) - 1;
                }
                if ((grid[r].chunks[c_chk] & mask) != mask) {
                    row_full = false;
                    break;
                }
            }
            
            if (row_full) {
                if (r == first_row_with_holes) first_row_with_holes++;
                r++;
                continue;
            }

            // Iterate through empty cells in this row
            for (int c = 0; c < W_grid; ++c) {
                if (!is_occupied(r, c)) {
                    // Try to place the piece with its "leading cell" at (r, c)
                    for (int t = 0; t < 8; ++t) {
                        const Transform& T = P.transforms[t];
                        bool ok = true;
                        
                        for (const auto& pt : T.offsets) {
                            int nr = r + pt.y;
                            int nc = c + pt.x;
                            if (nc >= W_grid || is_occupied(nr, nc)) {
                                ok = false; 
                                break;
                            }
                        }
                        
                        if (ok) {
                            // Valid placement found
                            for (const auto& pt : T.offsets) {
                                int nr = r + pt.y;
                                int nc = c + pt.x;
                                set_occupied(nr, nc);
                                if (nr > max_occupied_y) max_occupied_y = nr;
                                if (nc > max_occupied_x) max_occupied_x = nc;
                            }
                            
                            results[P.original_id] = {
                                c - T.min_tx, 
                                r - T.min_ty, 
                                T.R, 
                                T.F
                            };
                            placed = true;
                            break;
                        }
                    }
                    
                    if (placed) break;
                    
                    search_count++;
                    // If we searched too many holes/spots and couldn't fit,
                    // jump to the surface to append the piece there.
                    if (search_count > MAX_SEARCH_STEPS) {
                         r = max(r, max_occupied_y); 
                    }
                }
            }
            if (placed) break;
            r++;
        }
    }

    cout << (max_occupied_x + 1) << " " << (max_occupied_y + 1) << "\n";
    for (int i = 0; i < n; ++i) {
        cout << results[i].X << " " << results[i].Y << " " << results[i].R << " " << results[i].F << "\n";
    }

    return 0;
}