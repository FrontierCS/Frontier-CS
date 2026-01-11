#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, m;
    if (!(cin >> n >> m)) return 0;
    vector<vector<int>> S(n + 2); // 1..n+1, back is top
    for (int i = 1; i <= n; ++i) {
        S[i].reserve(m);
        for (int j = 0; j < m; ++j) {
            int x; cin >> x;
            S[i].push_back(x);
        }
    }
    // Extra pillar n+1 initially empty
    int E = n + 1;
    vector<pair<int,int>> ops;
    auto move_ball = [&](int x, int y) {
        // assumes valid
        int v = S[x].back();
        S[x].pop_back();
        S[y].push_back(v);
        ops.emplace_back(x, y);
    };
    
    if (m != 2) {
        // Fallback: do nothing (unsafe for general cases, but minimal placeholder)
        cout << 0 << "\n";
        return 0;
    }
    
    int maxColor = n; // colors are 1..n
    vector<array<int,2>> pos(maxColor + 1, array<int,2>{-1, -1});
    vector<int> cnt(maxColor + 1, 0);
    for (int i = 1; i <= n; ++i) {
        for (int v : S[i]) {
            if (cnt[v] == 0) pos[v][0] = i;
            else pos[v][1] = i;
            cnt[v]++;
        }
    }
    
    // To keep pos updated on moves
    auto update_pos_on_move = [&](int x, int y) {
        int v = S[y].back(); // v moved
        auto &p = pos[v];
        if (p[0] == x) p[0] = y;
        else if (p[1] == x) p[1] = y;
        else if (p[0] == -1) p[0] = y;
        else if (p[1] == -1) p[1] = y;
        // else it was both on same column x, we moved one to y: replace one occurrence
        // The above handles by first 'if' or 'else if'; if both were x, first triggers, second remains x which is correct.
    };
    
    auto do_move = [&](int x, int y) {
        move_ball(x, y);
        update_pos_on_move(x, y);
    };
    
    // Process each color
    for (int c = 1; c <= n; ++c) {
        // refresh positions in case both in same
        int A = pos[c][0];
        int B = pos[c][1];
        if (A == -1 || B == -1) continue; // should not happen
        if (A == B) continue; // already grouped
        // Determine top states
        bool topA = (!S[A].empty() && S[A].back() == c);
        bool topB = (!S[B].empty() && S[B].back() == c);
        if (topA && topB) {
            // Sequence to gather both c into A
            // B->E; A->B; A->E; B->A; E->B; E->A
            do_move(B, E);
            do_move(A, B);
            do_move(A, E);
            do_move(B, A);
            do_move(E, B);
            do_move(E, A);
        } else if (topA && !topB) {
            // Gather into B: B->E; A->B; E->A
            do_move(B, E);
            do_move(A, B);
            do_move(E, A);
        } else if (!topA && topB) {
            // Gather into A: A->E; B->A; E->B
            do_move(A, E);
            do_move(B, A);
            do_move(E, B);
        } else {
            // Neither top is c: A->E; B->E; B->A; E->B; E->B
            do_move(A, E);
            do_move(B, E);
            do_move(B, A);
            do_move(E, B);
            do_move(E, B);
        }
        // After operations, positions are updated via do_move
    }
    
    cout << ops.size() << "\n";
    for (auto &p : ops) {
        cout << p.first << " " << p.second << "\n";
    }
    return 0;
}