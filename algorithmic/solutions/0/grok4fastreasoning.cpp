#include <bits/stdc++.h>
using namespace std;

struct Piece {
    int best_F, best_R, min_tx, min_ty, bb_w, bb_h;
};

struct Pack {
    int idx, w, h;
};

bool can_pack(int W, int H, const vector<Pack>& sorted_pieces) {
    int n = sorted_pieces.size();
    int cur_y = 0;
    int cur_x = 0;
    int level_h = 0;
    for (int i = 0; i < n; ++i) {
        int pw = sorted_pieces[i].w;
        int ph = sorted_pieces[i].h;
        bool fits = (level_h > 0) && (cur_x + pw <= W) && (ph <= level_h);
        if (!fits) {
            cur_y += level_h;
            if (cur_y + ph > H) return false;
            level_h = ph;
            cur_x = 0;
        }
        cur_x += pw;
    }
    cur_y += level_h;
    return cur_y <= H;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    cin >> n;
    vector<Piece> pieces(n);
    int total_S = 0;
    int max_single_w = 0;
    for (int i = 0; i < n; ++i) {
        int k;
        cin >> k;
        total_S += k;
        vector<pair<int, int>> cells(k);
        for (int j = 0; j < k; ++j) {
            int x, y;
            cin >> x >> y;
            cells[j] = {x, y};
        }
        int best_h = INT_MAX;
        int best_w = INT_MAX;
        int best_F = 0, best_R = 0;
        int best_min_tx = 0, best_min_ty = 0;
        for (int f = 0; f < 2; ++f) {
            for (int r = 0; r < 4; ++r) {
                int min_tx = INT_MAX, max_tx = INT_MIN;
                int min_ty = INT_MAX, max_ty = INT_MIN;
                for (auto [ox, oy] : cells) {
                    int tx = f ? -ox : ox;
                    int ty = oy;
                    for (int rr = 0; rr < r; ++rr) {
                        int ntx = ty;
                        int nty = -tx;
                        tx = ntx;
                        ty = nty;
                    }
                    min_tx = min(min_tx, tx);
                    max_tx = max(max_tx, tx);
                    min_ty = min(min_ty, ty);
                    max_ty = max(max_ty, ty);
                }
                int cw = max_tx - min_tx + 1;
                int ch = max_ty - min_ty + 1;
                bool better = (ch < best_h) || (ch == best_h && cw < best_w);
                if (better) {
                    best_h = ch;
                    best_w = cw;
                    best_F = f;
                    best_R = r;
                    best_min_tx = min_tx;
                    best_min_ty = min_ty;
                }
            }
        }
        pieces[i] = {best_F, best_R, best_min_tx, best_min_ty, best_w, best_h};
        max_single_w = max(max_single_w, best_w);
    }
    
    vector<Pack> sorted_pieces(n);
    for (int i = 0; i < n; ++i) {
        sorted_pieces[i].idx = i;
        sorted_pieces[i].w = pieces[i].bb_w;
        sorted_pieces[i].h = pieces[i].bb_h;
    }
    sort(sorted_pieces.begin(), sorted_pieces.end(), [](const Pack& a, const Pack& b) {
        if (a.h != b.h) return a.h > b.h;
        return a.w < b.w;
    });
    
    int best_A = INT_MAX;
    int best_H = INT_MAX;
    int best_W = INT_MAX;
    int max_cand = 2000;
    int est = (int)ceil(sqrt(total_S)) + 10;
    max_cand = max(max_cand, est * 2);
    int min_H = 0;
    for (auto& p : sorted_pieces) min_H = max(min_H, p.h);
    for (int cand_H = min_H; cand_H <= max_cand; ++cand_H) {
        int low = max(max_single_w, (total_S + cand_H - 1) / cand_H);
        int high = total_S;
        int min_W_for_H = -1;
        while (low <= high) {
            int mid = low + (high - low) / 2;
            if (can_pack(mid, cand_H, sorted_pieces)) {
                min_W_for_H = mid;
                high = mid - 1;
            } else {
                low = mid + 1;
            }
        }
        if (min_W_for_H != -1) {
            int A = min_W_for_H * cand_H;
            bool update = (A < best_A) ||
                          (A == best_A && cand_H < best_H) ||
                          (A == best_A && cand_H == best_H && min_W_for_H < best_W);
            if (update) {
                best_A = A;
                best_H = cand_H;
                best_W = min_W_for_H;
            }
        }
    }
    
    // Now perform placement
    vector<pair<int, int>> bb_pos(n, {-1, -1});
    int cur_y = 0;
    int cur_x = 0;
    int level_h = 0;
    for (int si = 0; si < n; ++si) {
        int idx = sorted_pieces[si].idx;
        int pw = sorted_pieces[si].w;
        int ph = sorted_pieces[si].h;
        bool fits = (level_h > 0) && (cur_x + pw <= best_W) && (ph <= level_h);
        if (!fits) {
            cur_y += level_h;
            level_h = ph;
            cur_x = 0;
        }
        int place_x = cur_x;
        int place_y = cur_y;
        cur_x += pw;
        bb_pos[idx] = {place_x, place_y};
    }
    
    cout << best_W << " " << best_H << "\n";
    for (int i = 0; i < n; ++i) {
        auto [px, py] = bb_pos[i];
        int X = px - pieces[i].min_tx;
        int Y = py - pieces[i].min_ty;
        cout << X << " " << Y << " " << pieces[i].best_R << " " << pieces[i].best_F << "\n";
    }
    
    return 0;
}