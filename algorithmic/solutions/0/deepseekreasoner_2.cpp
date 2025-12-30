#include <bits/stdc++.h>
using namespace std;

struct Point {
    int x, y;
    Point() {}
    Point(int x, int y) : x(x), y(y) {}
    bool operator<(const Point& p) const {
        return x < p.x || (x == p.x && y < p.y);
    }
};

struct Orientation {
    vector<Point> cells; // normalized coordinates (dx, dy)
    int w, h;           // width and height of bounding box
    int R, F;           // rotation and reflection parameters
    int off_x, off_y;   // offsets: min_x and min_y before normalization
};

struct Piece {
    int idx;            // original index
    int k;              // number of cells
    vector<Orientation> orientations;
};

// Apply transformation: reflection (if F=1) then rotation R (counterclockwise)
vector<Point> transform(const vector<Point>& orig, int R, int F) {
    vector<Point> res;
    for (const Point& p : orig) {
        int x = p.x, y = p.y;
        if (F == 1) {
            x = -x; // reflect across y-axis
        }
        // rotate counterclockwise R times
        if (R == 1) {
            int nx = -y, ny = x;
            x = nx; y = ny;
        } else if (R == 2) {
            x = -x; y = -y;
        } else if (R == 3) {
            int nx = y, ny = -x;
            x = nx; y = ny;
        }
        res.emplace_back(x, y);
    }
    return res;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);

    int n;
    cin >> n;
    vector<Piece> pieces(n);
    int total_cells = 0;
    for (int i = 0; i < n; ++i) {
        int k;
        cin >> k;
        total_cells += k;
        vector<Point> cells(k);
        for (int j = 0; j < k; ++j) {
            cin >> cells[j].x >> cells[j].y;
        }
        pieces[i].idx = i;
        pieces[i].k = k;
        // generate all 8 orientations
        for (int F : {0, 1}) {
            for (int R = 0; R < 4; ++R) {
                vector<Point> t = transform(cells, R, F);
                int min_x = t[0].x, min_y = t[0].y;
                int max_x = t[0].x, max_y = t[0].y;
                for (const Point& p : t) {
                    min_x = min(min_x, p.x);
                    min_y = min(min_y, p.y);
                    max_x = max(max_x, p.x);
                    max_y = max(max_y, p.y);
                }
                Orientation orient;
                orient.R = R;
                orient.F = F;
                orient.off_x = min_x;
                orient.off_y = min_y;
                orient.w = max_x - min_x + 1;
                orient.h = max_y - min_y + 1;
                for (const Point& p : t) {
                    orient.cells.emplace_back(p.x - min_x, p.y - min_y);
                }
                pieces[i].orientations.push_back(orient);
            }
        }
    }

    // sort pieces by number of cells descending
    sort(pieces.begin(), pieces.end(), [](const Piece& a, const Piece& b) {
        return a.k > b.k;
    });

    // initial square side
    int S = max(10, (int)ceil(sqrt(total_cells)));
    // grid of occupied cells
    vector<vector<char>> grid(S, vector<char>(S, 0));
    int cur_x = 0, cur_y = 0;
    int max_x_used = -1, max_y_used = -1;

    // storage for final placements (in original order)
    struct Placement {
        int X, Y, R, F;
    };
    vector<Placement> placements(n);

    for (Piece& piece : pieces) {
        bool placed = false;
        while (!placed) {
            // try each orientation (sorted by bounding box area ascending)
            vector<Orientation>& orients = piece.orientations;
            sort(orients.begin(), orients.end(), [](const Orientation& a, const Orientation& b) {
                return a.w * a.h < b.w * b.h;
            });
            for (const Orientation& orient : orients) {
                // check if fits at (cur_x, cur_y)
                bool fits = true;
                for (const Point& p : orient.cells) {
                    int nx = cur_x + p.x;
                    int ny = cur_y + p.y;
                    if (nx < 0 || nx >= S || ny < 0 || ny >= S || grid[ny][nx]) {
                        fits = false;
                        break;
                    }
                }
                if (fits) {
                    // place the piece
                    for (const Point& p : orient.cells) {
                        int nx = cur_x + p.x;
                        int ny = cur_y + p.y;
                        grid[ny][nx] = 1;
                        max_x_used = max(max_x_used, nx);
                        max_y_used = max(max_y_used, ny);
                    }
                    placements[piece.idx] = {
                        cur_x - orient.off_x,
                        cur_y - orient.off_y,
                        orient.R,
                        orient.F
                    };
                    // advance cur_x by the width of the placed piece
                    cur_x += orient.w;
                    placed = true;
                    break;
                }
            }
            if (!placed) {
                // move to next position
                ++cur_x;
                if (cur_x >= S) {
                    cur_x = 0;
                    ++cur_y;
                    if (cur_y >= S) {
                        // expand the grid
                        int new_S = S + 10;
                        grid.resize(new_S);
                        for (int i = 0; i < new_S; ++i) {
                            if (i < S) {
                                grid[i].resize(new_S, 0);
                            } else {
                                grid[i].resize(new_S, 0);
                            }
                        }
                        S = new_S;
                    }
                }
            }
        }
    }

    int W = max_x_used + 1;
    int H = max_y_used + 1;
    cout << W << " " << H << "\n";
    for (int i = 0; i < n; ++i) {
        const Placement& pl = placements[i];
        cout << pl.X << " " << pl.Y << " " << pl.R << " " << pl.F << "\n";
    }

    return 0;
}