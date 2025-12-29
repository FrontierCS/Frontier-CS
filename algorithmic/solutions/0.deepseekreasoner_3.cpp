#include <bits/stdc++.h>
using namespace std;

struct Orientation {
    int f, r;
    int w, h;
    vector<pair<int,int>> cells; // (dx, dy) normalized to min (0,0)
};

vector<Orientation> generate_orientations(const vector<pair<int,int>>& orig) {
    set<vector<pair<int,int>>> seen;
    vector<Orientation> res;
    for (int f = 0; f < 2; ++f) {
        for (int r = 0; r < 4; ++r) {
            vector<pair<int,int>> transformed;
            for (auto [x, y] : orig) {
                int nx = x, ny = y;
                if (f) nx = -nx;
                for (int rot = 0; rot < r; ++rot) {
                    int tx = ny;
                    int ty = -nx;
                    nx = tx; ny = ty;
                }
                transformed.emplace_back(nx, ny);
            }
            // normalize
            int minx = INT_MAX, miny = INT_MAX;
            for (auto& p : transformed) {
                minx = min(minx, p.first);
                miny = min(miny, p.second);
            }
            for (auto& p : transformed) {
                p.first -= minx;
                p.second -= miny;
            }
            sort(transformed.begin(), transformed.end());
            if (seen.count(transformed)) continue;
            seen.insert(transformed);
            Orientation o;
            o.f = f; o.r = r;
            int maxx = 0, maxy = 0;
            for (auto& p : transformed) {
                maxx = max(maxx, p.first);
                maxy = max(maxy, p.second);
            }
            o.w = maxx + 1;
            o.h = maxy + 1;
            o.cells = transformed;
            res.push_back(o);
        }
    }
    return res;
}

tuple<bool, int, vector<tuple<int,int,int,int>>> 
pack(int W, const vector<int>& sorted_indices, const vector<vector<Orientation>>& piece_orientations) {
    int n = piece_orientations.size();
    vector<int> height(W, -1);
    vector<tuple<int,int,int,int>> placements(n);
    for (int idx : sorted_indices) {
        int best_y = INT_MAX;
        int best_x = INT_MAX;
        const Orientation* best_orient = nullptr;
        for (const auto& orient : piece_orientations[idx]) {
            if (orient.w > W) continue;
            for (int x = 0; x <= W - orient.w; ++x) {
                int y_req = 0;
                for (const auto& cell : orient.cells) {
                    int col = x + cell.first;
                    int y_needed = height[col] - cell.second + 1;
                    if (y_needed > y_req) y_req = y_needed;
                }
                if (y_req < best_y || (y_req == best_y && x < best_x)) {
                    best_y = y_req;
                    best_x = x;
                    best_orient = &orient;
                }
            }
        }
        if (!best_orient) {
            return {false, 0, {}};
        }
        for (const auto& cell : best_orient->cells) {
            int col = best_x + cell.first;
            int y_cell = best_y + cell.second;
            if (y_cell > height[col]) height[col] = y_cell;
        }
        placements[idx] = {best_x, best_y, best_orient->r, best_orient->f};
    }
    int H = *max_element(height.begin(), height.end()) + 1;
    return {true, H, placements};
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    cin >> n;
    vector<vector<pair<int,int>>> pieces(n);
    vector<int> ks(n);
    long long total_cells = 0;
    for (int i = 0; i < n; ++i) {
        int k;
        cin >> k;
        ks[i] = k;
        total_cells += k;
        pieces[i].resize(k);
        for (int j = 0; j < k; ++j) {
            cin >> pieces[i][j].first >> pieces[i][j].second;
        }
    }
    
    vector<vector<Orientation>> orientations(n);
    for (int i = 0; i < n; ++i) {
        orientations[i] = generate_orientations(pieces[i]);
    }
    
    vector<int> sorted_indices(n);
    iota(sorted_indices.begin(), sorted_indices.end(), 0);
    sort(sorted_indices.begin(), sorted_indices.end(), [&](int a, int b) {
        return ks[a] > ks[b];
    });
    
    int baseW = max(10, (int)ceil(sqrt(total_cells)));
    int best_area = INT_MAX, best_H = 0, best_W = 0;
    vector<tuple<int,int,int,int>> best_placements;
    
    for (int delta : {-1, 0, 1}) {
        int W = baseW + delta;
        if (W < 10) continue;
        auto [success, H, placements] = pack(W, sorted_indices, orientations);
        if (!success) continue;
        int area = W * H;
        if (area < best_area || (area == best_area && H < best_H) ||
            (area == best_area && H == best_H && W < best_W)) {
            best_area = area;
            best_H = H;
            best_W = W;
            best_placements = placements;
        }
    }
    
    cout << best_W << " " << best_H << "\n";
    for (int i = 0; i < n; ++i) {
        auto [X, Y, R, F] = best_placements[i];
        cout << X << " " << Y << " " << R << " " << F << "\n";
    }
    
    return 0;
}