#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N, M;
    if (!(cin >> N >> M)) return 0;
    vector<int> I(M), J(M);
    for (int k = 0; k < M; k++) cin >> I[k] >> J[k];

    vector<pair<char,char>> out;
    int r = I[0], c = J[0];
    auto add_moves = [&](char dir, int cnt){
        for (int t = 0; t < cnt; t++) out.emplace_back('M', dir);
    };
    auto add_slide = [&](char dir){
        out.emplace_back('S', dir);
    };

    for (int k = 1; k < M; k++) {
        int tr = I[k], tc = J[k];
        int dr = abs(r - tr), dc = abs(c - tc);
        int dtbRow = min(tr, N - 1 - tr);
        int dtbCol = min(tc, N - 1 - tc);

        int cost0 = dr + dc;                    // all moves
        int cost1 = 1 + dtbRow + dc;            // slide vertical to nearest boundary to tr, then moves
        int cost2 = 1 + dr + dtbCol;            // slide horizontal to nearest boundary to tc, then moves
        int cost3 = 2 + dtbRow + dtbCol;        // slide vertical + slide horizontal, then moves

        int best = 0;
        int bestCost = cost0;
        if (cost1 < bestCost) { best = 1; bestCost = cost1; }
        if (cost2 < bestCost) { best = 2; bestCost = cost2; }
        if (cost3 < bestCost) { best = 3; bestCost = cost3; }

        if (best == 0) {
            if (r < tr) add_moves('D', tr - r);
            else if (r > tr) add_moves('U', r - tr);
            if (c < tc) add_moves('R', tc - c);
            else if (c > tc) add_moves('L', c - tc);
            r = tr; c = tc;
        } else if (best == 1) {
            // Slide vertical towards nearest boundary to tr
            if (tr <= (N - 1 - tr)) {
                add_slide('U');
                r = 0;
            } else {
                add_slide('D');
                r = N - 1;
            }
            if (r < tr) add_moves('D', tr - r);
            else if (r > tr) add_moves('U', r - tr);
            r = tr;
            if (c < tc) add_moves('R', tc - c);
            else if (c > tc) add_moves('L', c - tc);
            c = tc;
        } else if (best == 2) {
            // Slide horizontal towards nearest boundary to tc
            if (tc <= (N - 1 - tc)) {
                add_slide('L');
                c = 0;
            } else {
                add_slide('R');
                c = N - 1;
            }
            if (r < tr) add_moves('D', tr - r);
            else if (r > tr) add_moves('U', r - tr);
            r = tr;
            if (c < tc) add_moves('R', tc - c);
            else if (c > tc) add_moves('L', c - tc);
            c = tc;
        } else {
            // Two slides: vertical then horizontal to boundaries nearest to tr and tc
            if (tr <= (N - 1 - tr)) {
                add_slide('U');
                r = 0;
            } else {
                add_slide('D');
                r = N - 1;
            }
            if (tc <= (N - 1 - tc)) {
                add_slide('L');
                c = 0;
            } else {
                add_slide('R');
                c = N - 1;
            }
            if (r < tr) add_moves('D', tr - r);
            else if (r > tr) add_moves('U', r - tr);
            r = tr;
            if (c < tc) add_moves('R', tc - c);
            else if (c > tc) add_moves('L', c - tc);
            c = tc;
        }
    }

    int limit = 2 * N * M;
    if ((int)out.size() > limit) out.resize(limit);
    for (auto &p : out) {
        cout << p.first << ' ' << p.second << '\n';
    }
    return 0;
}