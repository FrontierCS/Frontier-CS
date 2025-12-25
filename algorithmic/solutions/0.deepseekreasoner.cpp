#include <iostream>
#include <vector>
#include <algorithm>
#include <set>
#include <cmath>
#include <cassert>

using namespace std;

struct Point {
    int x, y;
    Point(int x = 0, int y = 0) : x(x), y(y) {}
};

struct Candidate {
    int x, y;
    bool operator<(const Candidate& other) const {
        if (y != other.y) return y < other.y;
        return x < other.x;
    }
};

struct Orientation {
    int R, F;
    int width, height;
    vector<Point> cells;  // relative offsets (dx, dy)
};

struct Piece {
    int k;
    vector<Point> original;
    vector<Orientation> orientations;
};

struct Placement {
    int X, Y, R, F;
};

const int dx4[4] = {1, -1, 0, 0};
const int dy4[4] = {0, 0, 1, -1};

void generateOrientations(Piece& piece) {
    vector<Point>& pts = piece.original;
    for (int F = 0; F < 2; ++F) {
        for (int R = 0; R < 4; ++R) {
            vector<Point> transformed;
            for (const Point& p : pts) {
                int x = p.x, y = p.y;
                if (F) x = -x;
                // rotate R times clockwise
                if (R == 1) { int tmp = x; x = y; y = -tmp; }
                else if (R == 2) { x = -x; y = -y; }
                else if (R == 3) { int tmp = x; x = -y; y = tmp; }
                transformed.emplace_back(x, y);
            }
            // normalize to non‑negative coordinates
            int min_x = transformed[0].x, min_y = transformed[0].y;
            for (const Point& p : transformed) {
                min_x = min(min_x, p.x);
                min_y = min(min_y, p.y);
            }
            vector<Point> cells;
            int max_x = min_x, max_y = min_y;
            for (Point& p : transformed) {
                int dx = p.x - min_x;
                int dy = p.y - min_y;
                cells.emplace_back(dx, dy);
                max_x = max(max_x, p.x);
                max_y = max(max_y, p.y);
            }
            int width = max_x - min_x + 1;
            int height = max_y - min_y + 1;
            piece.orientations.push_back({R, F, width, height, cells});
        }
    }
}

bool tryPack(int S, const vector<Piece>& pieces, const vector<int>& order,
             vector<Placement>& placements) {
    vector<vector<char>> occupied(S, vector<char>(S, 0));
    set<Candidate> candidates;
    candidates.insert({0, 0});

    for (int idx : order) {
        const Piece& piece = pieces[idx];
        bool placed = false;

        // Try candidates in order (lowest y, then x)
        for (auto it = candidates.begin(); it != candidates.end() && !placed; ) {
            Candidate c = *it;
            if (occupied[c.x][c.y]) {
                it = candidates.erase(it);
                continue;
            }
            for (const Orientation& orient : piece.orientations) {
                if (c.x + orient.width > S || c.y + orient.height > S) continue;
                bool fits = true;
                for (const Point& cell : orient.cells) {
                    int nx = c.x + cell.x;
                    int ny = c.y + cell.y;
                    if (nx < 0 || nx >= S || ny < 0 || ny >= S || occupied[nx][ny]) {
                        fits = false;
                        break;
                    }
                }
                if (fits) {
                    // Place the piece
                    for (const Point& cell : orient.cells) {
                        int nx = c.x + cell.x;
                        int ny = c.y + cell.y;
                        occupied[nx][ny] = 1;
                    }
                    placements[idx] = {c.x, c.y, orient.R, orient.F};
                    placed = true;
                    // Remove used candidate
                    it = candidates.erase(it);
                    // Add neighbouring empty cells to candidates
                    for (const Point& cell : orient.cells) {
                        int nx = c.x + cell.x;
                        int ny = c.y + cell.y;
                        for (int d = 0; d < 4; ++d) {
                            int nx2 = nx + dx4[d];
                            int ny2 = ny + dy4[d];
                            if (nx2 >= 0 && nx2 < S && ny2 >= 0 && ny2 < S && !occupied[nx2][ny2]) {
                                candidates.insert({nx2, ny2});
                            }
                        }
                    }
                    break;
                }
            }
            if (!placed) ++it;
        }

        // If still not placed, fallback to full grid scan
        if (!placed) {
            bool found = false;
            for (int y = 0; y < S && !found; ++y) {
                for (int x = 0; x < S && !found; ++x) {
                    if (occupied[x][y]) continue;
                    for (const Orientation& orient : piece.orientations) {
                        if (x + orient.width > S || y + orient.height > S) continue;
                        bool fits = true;
                        for (const Point& cell : orient.cells) {
                            int nx = x + cell.x;
                            int ny = y + cell.y;
                            if (nx < 0 || nx >= S || ny < 0 || ny >= S || occupied[nx][ny]) {
                                fits = false;
                                break;
                            }
                        }
                        if (fits) {
                            for (const Point& cell : orient.cells) {
                                int nx = x + cell.x;
                                int ny = y + cell.y;
                                occupied[nx][ny] = 1;
                            }
                            placements[idx] = {x, y, orient.R, orient.F};
                            placed = true;
                            found = true;
                            // Add neighbours
                            for (const Point& cell : orient.cells) {
                                int nx = x + cell.x;
                                int ny = y + cell.y;
                                for (int d = 0; d < 4; ++d) {
                                    int nx2 = nx + dx4[d];
                                    int ny2 = ny + dy4[d];
                                    if (nx2 >= 0 && nx2 < S && ny2 >= 0 && ny2 < S && !occupied[nx2][ny2]) {
                                        candidates.insert({nx2, ny2});
                                    }
                                }
                            }
                            break;
                        }
                    }
                }
            }
            if (!found) {
                return false;  // cannot place this piece in current square
            }
        }
    }
    return true;  // all pieces placed
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    cin >> n;
    vector<Piece> pieces(n);
    long long total_cells = 0;
    int max_min_side = 0;

    for (int i = 0; i < n; ++i) {
        int k;
        cin >> k;
        pieces[i].k = k;
        pieces[i].original.resize(k);
        for (int j = 0; j < k; ++j) {
            cin >> pieces[i].original[j].x >> pieces[i].original[j].y;
        }
        total_cells += k;
        generateOrientations(pieces[i]);
        // compute minimal side needed for this piece
        int min_side = 1000;
        for (const Orientation& orient : pieces[i].orientations) {
            int side = max(orient.width, orient.height);
            min_side = min(min_side, side);
        }
        max_min_side = max(max_min_side, min_side);
    }

    // initial square side lower bound
    int S_start = max((int)ceil(sqrt(total_cells)), max_min_side);
    vector<int> order(n);
    for (int i = 0; i < n; ++i) order[i] = i;
    sort(order.begin(), order.end(), [&](int a, int b) {
        return pieces[a].k > pieces[b].k;  // larger pieces first
    });

    vector<Placement> placements(n);
    int S = S_start;
    while (true) {
        if (tryPack(S, pieces, order, placements)) {
            break;
        }
        ++S;
    }

    cout << S << " " << S << "\n";
    for (int i = 0; i < n; ++i) {
        cout << placements[i].X << " " << placements[i].Y << " "
             << placements[i].R << " " << placements[i].F << "\n";
    }

    return 0;
}