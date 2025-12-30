#include <iostream>
#include <vector>
#include <algorithm>
#include <cmath>
#include <bitset>

using namespace std;

const int MAX_W_BITS = 512;

struct Point {
    int x, y;
    bool operator<(const Point& other) const {
        if (y != other.y) return y < other.y;
        return x < other.x;
    }
};

struct Polyomino {
    int id;
    int k;
    vector<Point> cells;
};

struct Variant {
    int id;
    int F, R;
    int w, h;
    int shift_x, shift_y;
    vector<Point> cells;
    vector<bitset<MAX_W_BITS>> masks; 

    bool operator==(const Variant& other) const {
        if (w != other.w || h != other.h) return false;
        for (size_t i = 0; i < cells.size(); ++i) {
            if (cells[i].x != other.cells[i].x || cells[i].y != other.cells[i].y)
                return false;
        }
        return true;
    }
};

struct Placement {
    int x, y;
    int F, R;
};

int N;
vector<Polyomino> pieces;
vector<vector<Variant>> piece_variants;
vector<Placement> solution;
int GRID_W;
vector<bitset<MAX_W_BITS>> grid;
int min_search_y = 0;

Point rotate(Point p) { return {-p.y, p.x}; } 
Point reflect(Point p) { return {-p.x, p.y}; } 

void generate_variants(int idx) {
    const auto& P = pieces[idx];
    piece_variants[idx].clear();
    
    vector<Point> current = P.cells;
    for (int f = 0; f < 2; ++f) {
        vector<Point> reflected = current;
        if (f == 1) {
            for (auto& p : reflected) p = reflect(p);
        }
        
        vector<Point> rotated = reflected;
        for (int r = 0; r < 4; ++r) {
            if (r > 0) {
                for (auto& p : rotated) p = rotate(p);
            }
            
            int min_x = 1000, max_x = -1000;
            int min_y = 1000, max_y = -1000;
            for (auto& p : rotated) {
                min_x = min(min_x, p.x);
                max_x = max(max_x, p.x);
                min_y = min(min_y, p.y);
                max_y = max(max_y, p.y);
            }
            
            Variant v;
            v.id = idx;
            v.F = f;
            v.R = r;
            v.w = max_x - min_x + 1;
            v.h = max_y - min_y + 1;
            v.shift_x = min_x;
            v.shift_y = min_y;
            
            for (auto& p : rotated) {
                v.cells.push_back({p.x - min_x, p.y - min_y});
            }
            sort(v.cells.begin(), v.cells.end());
            
            bool unique = true;
            for (const auto& existing : piece_variants[idx]) {
                if (existing == v) {
                    unique = false;
                    break;
                }
            }
            
            if (unique) {
                v.masks.resize(v.h);
                for (auto& p : v.cells) {
                    v.masks[p.y].set(p.x);
                }
                piece_variants[idx].push_back(v);
            }
        }
    }
}

bool can_place(const Variant& v, int x, int y) {
    if (x + v.w > GRID_W) return false;
    for (int i = 0; i < v.h; ++i) {
        if (y + i >= grid.size()) continue;
        if ((grid[y + i] & (v.masks[i] << x)).any()) return false;
    }
    return true;
}

void place_piece(const Variant& v, int x, int y) {
    if (y + v.h > grid.size()) {
        grid.resize(y + v.h + 50);
    }
    for (int i = 0; i < v.h; ++i) {
        grid[y + i] |= (v.masks[i] << x);
    }
    solution[v.id] = {x - v.shift_x, y - v.shift_y, v.F, v.R};
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> N)) return 0;

    pieces.resize(N);
    piece_variants.resize(N);
    solution.resize(N);

    long long total_area = 0;
    for (int i = 0; i < N; ++i) {
        pieces[i].id = i;
        cin >> pieces[i].k;
        pieces[i].cells.resize(pieces[i].k);
        for (int j = 0; j < pieces[i].k; ++j) {
            cin >> pieces[i].cells[j].x >> pieces[i].cells[j].y;
        }
        total_area += pieces[i].k;
        generate_variants(i);
    }

    int side = ceil(sqrt(total_area));
    GRID_W = max(side, 15);
    if (GRID_W > MAX_W_BITS) GRID_W = MAX_W_BITS;

    grid.resize(200);

    vector<int> p_indices(N);
    for(int i=0; i<N; ++i) p_indices[i] = i;
    
    sort(p_indices.begin(), p_indices.end(), [](int a, int b) {
        return pieces[a].k > pieces[b].k;
    });

    for (int idx : p_indices) {
        int best_x = -1, best_y = 1e9;
        int best_v_idx = -1;
        
        for (int v = 0; v < piece_variants[idx].size(); ++v) {
            const auto& var = piece_variants[idx][v];
            if (var.w > GRID_W) continue;

            int cur_y = min_search_y;
            bool placed = false;
            
            while (true) {
                if (cur_y > best_y) break;
                if (cur_y < grid.size() && grid[cur_y].count() == GRID_W) {
                    cur_y++;
                    continue;
                }
                
                for (int x = 0; x <= GRID_W - var.w; ++x) {
                    if (can_place(var, x, cur_y)) {
                        if (cur_y < best_y || (cur_y == best_y && x < best_x)) {
                            best_y = cur_y;
                            best_x = x;
                            best_v_idx = v;
                        }
                        placed = true;
                        break;
                    }
                }
                if (placed) break;
                cur_y++;
                if (cur_y > 10000) break; 
            }
        }
        
        if (best_v_idx != -1) {
            place_piece(piece_variants[idx][best_v_idx], best_x, best_y);
            while (min_search_y < grid.size() && grid[min_search_y].count() == GRID_W) {
                min_search_y++;
            }
        }
    }

    int final_W = 0;
    int final_H = 0;
    
    for (int y = 0; y < grid.size(); ++y) {
        if (grid[y].any()) {
            final_H = y + 1;
            for (int x = GRID_W - 1; x >= 0; --x) {
                if (grid[y].test(x)) {
                    final_W = max(final_W, x + 1);
                    break;
                }
            }
        }
    }

    cout << final_W << " " << final_H << "\n";
    for (int i = 0; i < N; ++i) {
        cout << solution[i].x << " " << solution[i].y << " " << solution[i].R << " " << solution[i].F << "\n";
    }

    return 0;
}