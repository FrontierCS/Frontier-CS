#include <iostream>
#include <vector>
#include <algorithm>
#include <cmath>
#include <set>
#include <climits>

using namespace std;

struct Orientation {
    int R, F;
    int min_tx, min_ty;
    int width, height;
    vector<pair<int, int>> cells; // normalized, sorted
};

struct Polyomino {
    int id;
    int k;
    vector<pair<int, int>> orig;
    vector<Orientation> orientations;
};

// Apply transformation: reflect (if F=1) then rotate clockwise by R*90°
pair<int, int> transform(int x, int y, int F, int R) {
    if (F) x = -x;
    int nx, ny;
    switch (R) {
        case 0: nx = x; ny = y; break;
        case 1: nx = y; ny = -x; break;
        case 2: nx = -x; ny = -y; break;
        case 3: nx = -y; ny = x; break;
        default: return {0,0};
    }
    return {nx, ny};
}

void generateOrientations(Polyomino& poly) {
    set<vector<pair<int, int>>> seen;
    for (int F = 0; F <= 1; ++F) {
        for (int R = 0; R < 4; ++R) {
            vector<pair<int, int>> transformed;
            for (auto& p : poly.orig) {
                transformed.push_back(transform(p.first, p.second, F, R));
            }
            int minx = transformed[0].first, miny = transformed[0].second;
            int maxx = minx, maxy = miny;
            for (auto& p : transformed) {
                minx = min(minx, p.first);
                miny = min(miny, p.second);
                maxx = max(maxx, p.first);
                maxy = max(maxy, p.second);
            }
            int width = maxx - minx + 1;
            int height = maxy - miny + 1;
            // normalize
            vector<pair<int, int>> normalized;
            for (auto& p : transformed) {
                normalized.push_back({p.first - minx, p.second - miny});
            }
            sort(normalized.begin(), normalized.end());
            if (seen.find(normalized) == seen.end()) {
                seen.insert(normalized);
                poly.orientations.push_back({R, F, minx, miny, width, height, normalized});
            }
        }
    }
}

struct Result {
    int W, H, area;
    vector<int> orient_idx;
    vector<pair<int, int>> placements; // (x,y) of bounding box bottom-left
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    cin >> n;
    vector<Polyomino> polys(n);
    int total_cells = 0;
    for (int i = 0; i < n; ++i) {
        int k;
        cin >> k;
        total_cells += k;
        vector<pair<int, int>> cells(k);
        for (int j = 0; j < k; ++j) {
            cin >> cells[j].first >> cells[j].second;
        }
        polys[i] = {i, k, cells, {}};
        generateOrientations(polys[i]);
    }

    // Compute minimum width needed so that every piece has at least one orientation that fits.
    int W_min_needed = 0;
    for (auto& poly : polys) {
        int minw = INT_MAX;
        for (auto& o : poly.orientations)
            minw = min(minw, o.width);
        W_min_needed = max(W_min_needed, minw);
    }

    int base = (int)sqrt(total_cells);
    set<int> candidate_set;
    candidate_set.insert(W_min_needed);
    candidate_set.insert(base);
    if (base - 1 >= W_min_needed) candidate_set.insert(base - 1);
    if (base + 1 >= W_min_needed) candidate_set.insert(base + 1);
    vector<double> factors = {0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.5, 2.0, 3.0};
    for (double f : factors) {
        int w = max(W_min_needed, (int)(base * f));
        candidate_set.insert(w);
    }
    // Add some more candidates near the lower bound
    for (int w = W_min_needed; w <= min(W_min_needed + 10, base); ++w) {
        candidate_set.insert(w);
    }
    vector<int> candidates(candidate_set.begin(), candidate_set.end());

    Result best;
    best.area = INT_MAX;

    for (int W : candidates) {
        // For each polyomino, choose the best orientation for this W.
        vector<int> orient_idx(n, -1);
        bool ok = true;
        for (int i = 0; i < n; ++i) {
            int best_h = INT_MAX;
            int best_a = INT_MAX;
            int best_j = -1;
            for (int j = 0; j < polys[i].orientations.size(); ++j) {
                Orientation& o = polys[i].orientations[j];
                if (o.width > W) continue;
                if (o.height < best_h || (o.height == best_h && o.width * o.height < best_a)) {
                    best_h = o.height;
                    best_a = o.width * o.height;
                    best_j = j;
                }
            }
            if (best_j == -1) {
                ok = false;
                break;
            }
            orient_idx[i] = best_j;
        }
        if (!ok) continue;

        // Build list of rectangles (bounding boxes) for the chosen orientations.
        struct RectItem {
            int id, w, h;
        };
        vector<RectItem> rects;
        for (int i = 0; i < n; ++i) {
            Orientation& o = polys[i].orientations[orient_idx[i]];
            rects.push_back({i, o.width, o.height});
        }
        // Sort by height descending (standard NFDH).
        sort(rects.begin(), rects.end(),
             [](const RectItem& a, const RectItem& b) { return a.h > b.h; });

        // NFDH packing.
        int cur_x = 0, cur_row_h = 0, total_h = 0;
        vector<pair<int, int>> placements(n);
        for (auto& r : rects) {
            if (cur_x + r.w > W) {
                total_h += cur_row_h;
                cur_x = 0;
                cur_row_h = 0;
            }
            placements[r.id] = {cur_x, total_h};
            cur_x += r.w;
            cur_row_h = max(cur_row_h, r.h);
        }
        total_h += cur_row_h;
        int H = total_h;
        int area = W * H;

        // Update best result.
        if (area < best.area ||
            (area == best.area && H < best.H) ||
            (area == best.area && H == best.H && W < best.W)) {
            best.W = W;
            best.H = H;
            best.area = area;
            best.orient_idx = orient_idx;
            best.placements = placements;
        }
    }

    // Output the best found packing.
    cout << best.W << " " << best.H << "\n";
    for (int i = 0; i < n; ++i) {
        Orientation& o = polys[i].orientations[best.orient_idx[i]];
        int x = best.placements[i].first;
        int y = best.placements[i].second;
        int X = x - o.min_tx;
        int Y = y - o.min_ty;
        cout << X << " " << Y << " " << o.R << " " << o.F << "\n";
    }

    return 0;
}