#include <bits/stdc++.h>
using namespace std;

struct Orientation {
    vector<pair<int,int>> cells;  // normalized cells
    int shift_x, shift_y;         // min_x, min_y subtracted during normalization
    int rot;
    bool reflect;
    int w, h;                     // bounding box dimensions (from normalized cells)
};

struct Piece {
    int id;                       // original index
    int k;
    vector<Orientation> orientations;
};

// Apply transformation: reflection (across y-axis) then counter‑clockwise rotation.
void apply_transform(int x, int y, bool reflect, int rot, int& ox, int& oy) {
    if (reflect) x = -x;
    for (int r = 0; r < rot; ++r) {
        int nx = -y;
        int ny =  x;
        x = nx;
        y = ny;
    }
    ox = x;
    oy = y;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    cin >> n;
    vector<Piece> pieces(n);
    int total_cells = 0;

    // Read pieces and generate all distinct orientations.
    for (int i = 0; i < n; ++i) {
        int k;
        cin >> k;
        pieces[i].id = i;
        pieces[i].k = k;
        vector<pair<int,int>> cells(k);
        for (int j = 0; j < k; ++j) {
            cin >> cells[j].first >> cells[j].second;
        }

        set<vector<pair<int,int>>> seen;
        for (int reflect = 0; reflect <= 1; ++reflect) {
            for (int rot = 0; rot < 4; ++rot) {
                vector<pair<int,int>> transformed;
                for (auto& p : cells) {
                    int x, y;
                    apply_transform(p.first, p.second, reflect, rot, x, y);
                    transformed.push_back({x, y});
                }

                // Normalize to non‑negative coordinates.
                int min_x = transformed[0].first, min_y = transformed[0].second;
                for (auto& p : transformed) {
                    min_x = min(min_x, p.first);
                    min_y = min(min_y, p.second);
                }
                vector<pair<int,int>> normalized;
                for (auto& p : transformed) {
                    normalized.push_back({p.first - min_x, p.second - min_y});
                }
                sort(normalized.begin(), normalized.end());
                if (seen.count(normalized)) continue;
                seen.insert(normalized);

                // Compute bounding box.
                int max_x = normalized[0].first, max_y = normalized[0].second;
                for (auto& p : normalized) {
                    max_x = max(max_x, p.first);
                    max_y = max(max_y, p.second);
                }
                int w = max_x + 1, h = max_y + 1;

                Orientation orient;
                orient.cells = normalized;
                orient.shift_x = min_x;
                orient.shift_y = min_y;
                orient.rot = rot;
                orient.reflect = reflect;
                orient.w = w;
                orient.h = h;
                pieces[i].orientations.push_back(orient);
            }
        }

        // Sort orientations by bounding box area (smaller first).
        sort(pieces[i].orientations.begin(), pieces[i].orientations.end(),
             [](const Orientation& a, const Orientation& b) {
                 return a.w * a.h < b.w * b.h;
             });

        total_cells += k;
    }

    // Order pieces by decreasing size (largest first).
    vector<int> order(n);
    iota(order.begin(), order.end(), 0);
    sort(order.begin(), order.end(), [&](int a, int b) {
        return pieces[a].k > pieces[b].k;
    });

    int S0 = (int)ceil(sqrt(total_cells));
    int max_try = S0 + 500;   // upper bound for square side length
    vector<tuple<int,int,int>> placements(n);  // (anchor_x, anchor_y, orientation_index)

    for (int S = S0; S <= max_try; ++S) {
        vector<vector<char>> occ(S, vector<char>(S, 0));
        bool ok = true;

        for (int idx : order) {
            Piece& piece = pieces[idx];
            bool placed = false;

            for (int y = 0; y < S && !placed; ++y) {
                for (int x = 0; x < S && !placed; ++x) {
                    if (occ[y][x]) continue;

                    for (size_t oi = 0; oi < piece.orientations.size(); ++oi) {
                        Orientation& orient = piece.orientations[oi];
                        if (x + orient.w > S || y + orient.h > S) continue;

                        bool fit = true;
                        for (auto& cell : orient.cells) {
                            int nx = x + cell.first;
                            int ny = y + cell.second;
                            if (nx < 0 || nx >= S || ny < 0 || ny >= S || occ[ny][nx]) {
                                fit = false;
                                break;
                            }
                        }
                        if (fit) {
                            for (auto& cell : orient.cells) {
                                int nx = x + cell.first;
                                int ny = y + cell.second;
                                occ[ny][nx] = 1;
                            }
                            placements[idx] = {x, y, (int)oi};
                            placed = true;
                            break;
                        }
                    }
                }
            }

            if (!placed) {
                ok = false;
                break;
            }
        }

        if (ok) {
            cout << S << " " << S << "\n";
            for (int i = 0; i < n; ++i) {
                auto [ax, ay, oi] = placements[i];
                Orientation& orient = pieces[i].orientations[oi];
                int X = ax - orient.shift_x;
                int Y = ay - orient.shift_y;
                cout << X << " " << Y << " " << orient.rot << " " << (orient.reflect ? 1 : 0) << "\n";
            }
            return 0;
        }
    }

    // Fallback (should rarely be needed): pack into a huge square.
    int S = total_cells;
    vector<vector<char>> occ(S, vector<char>(S, 0));
    for (int idx : order) {
        Piece& piece = pieces[idx];
        bool placed = false;
        for (int y = 0; y < S && !placed; ++y) {
            for (int x = 0; x < S && !placed; ++x) {
                if (occ[y][x]) continue;
                for (size_t oi = 0; oi < piece.orientations.size(); ++oi) {
                    Orientation& orient = piece.orientations[oi];
                    if (x + orient.w > S || y + orient.h > S) continue;
                    bool fit = true;
                    for (auto& cell : orient.cells) {
                        int nx = x + cell.first;
                        int ny = y + cell.second;
                        if (nx < 0 || nx >= S || ny < 0 || ny >= S || occ[ny][nx]) {
                            fit = false;
                            break;
                        }
                    }
                    if (fit) {
                        for (auto& cell : orient.cells) {
                            int nx = x + cell.first;
                            int ny = y + cell.second;
                            occ[ny][nx] = 1;
                        }
                        placements[idx] = {x, y, (int)oi};
                        placed = true;
                        break;
                    }
                }
            }
        }
    }

    cout << S << " " << S << "\n";
    for (int i = 0; i < n; ++i) {
        auto [ax, ay, oi] = placements[i];
        Orientation& orient = pieces[i].orientations[oi];
        int X = ax - orient.shift_x;
        int Y = ay - orient.shift_y;
        cout << X << " " << Y << " " << orient.rot << " " << (orient.reflect ? 1 : 0) << "\n";
    }

    return 0;
}