#include <bits/stdc++.h>
using namespace std;

// Heuristic solver for Ball Moving Game
// NOTE: This is a heuristic and may not guarantee solution for all inputs.

struct State {
    int n, m;
    vector<vector<int>> st;
    vector<pair<int,int>> ops;
    int maxOps = 10000000;
    mt19937 rng;

    State(int n_, int m_, const vector<vector<int>>& init)
        : n(n_), m(m_), st(init), rng(123456789) {}

    bool isUniformColumn(int c) {
        if (st[c].empty()) return true;
        int col = st[c][0];
        for (int x : st[c]) if (x != col) return false;
        return true;
    }

    bool isGoal() {
        vector<int> owner(n+1, -1); // owner[color]
        for (int i=0;i<=n;i++) {
            if (st[i].empty()) continue;
            int c = st[i][0];
            for (int x : st[i]) {
                if (x != c) return false;
            }
            if (owner[c] == -1) owner[c] = i;
            else if (owner[c] != i) return false;
        }
        // each color must appear exactly m times
        vector<int> cnt(n+1,0);
        for (int i=0;i<=n;i++) {
            for (int x: st[i]) cnt[x]++;
        }
        for (int c=1;c<=n;c++) if (cnt[c] != m) return false;
        return true;
    }

    void doMove(int x, int y) {
        int ball = st[x].back();
        st[x].pop_back();
        st[y].push_back(ball);
        ops.emplace_back(x+1, y+1);
    }

    pair<int,int> randomMove() {
        vector<pair<int,int>> cand;
        for (int i=0;i<=n;i++) if (!st[i].empty()) {
            for (int j=0;j<=n;j++) if (i!=j && (int)st[j].size()<m) {
                // avoid breaking a perfect column if possible
                int c = st[i].back();
                if (isUniformColumn(i) && (int)st[i].size()==m) {
                    // moving from a completed column is bad, but maybe unavoidable
                    continue;
                }
                cand.emplace_back(i,j);
            }
        }
        if (cand.empty()) return {-1,-1};
        uniform_int_distribution<int> dist(0, (int)cand.size()-1);
        return cand[dist(rng)];
    }

    bool greedyStep(const vector<int>& home, pair<int,int> lastMove) {
        int bestScore = INT_MIN;
        pair<int,int> best(-1,-1);
        for (int i=0;i<=n;i++) {
            if (st[i].empty()) continue;
            int color = st[i].back();
            for (int j=0;j<=n;j++) {
                if (i==j) continue;
                if ((int)st[j].size()>=m) continue;
                int s = 0;
                bool jEmpty = st[j].empty();
                bool iUniform = isUniformColumn(i);
                bool jUniform = isUniformColumn(j);
                int topj = jEmpty ? -1 : st[j].back();
                int topiBelow = (int)st[i].size()>=2 ? st[i][st[i].size()-2] : -1;

                if (j == home[color]) s += 10;
                if (jEmpty) s += 5;
                if (!jEmpty && topj == color) s += 8;
                if (jUniform && (jEmpty || topj == color)) s += 3;
                if ((int)st[i].size()==1) s += 2; // emptying column helpful

                // avoid breaking good columns
                if (iUniform && st[i][0]==color && (int)st[i].size()==m) s -= 100;
                if (jUniform && !jEmpty && topj!=color) s -= 50;

                // avoid moves undoing previous
                if (lastMove.first == j && lastMove.second == i) s -= 5;

                // avoid stacking different colors on almost-finished column
                if (!jEmpty && jUniform && topj!=color) s -= 20;

                // prefer moving top if below is different color
                if (topiBelow != -1 && topiBelow != color) s += 1;

                if (s > bestScore) {
                    bestScore = s;
                    best = {i,j};
                }
            }
        }
        if (best.first == -1) return false;
        doMove(best.first, best.second);
        return true;
    }

    void solve() {
        // build home column as one with max count for each color
        vector<int> home(n+1,0);
        vector<vector<int>> countCol(n+1, vector<int>(n+1,0));
        for (int i=0;i<=n;i++) {
            for (int x: st[i]) if (1<=x && x<=n) countCol[x][i]++;
        }
        for (int c=1;c<=n;c++) {
            int best=-1, idx=0;
            for (int i=0;i<n;i++) { // don't choose buffer as home
                if (countCol[c][i]>best) {
                    best = countCol[c][i];
                    idx = i;
                }
            }
            home[c]=idx;
        }

        pair<int,int> lastMove(-1,-1);
        int stagnation = 0;
        while (!isGoal() && (int)ops.size() < maxOps) {
            int beforeOps = ops.size();
            bool moved = greedyStep(home, lastMove);
            if (!moved) {
                auto mv = randomMove();
                if (mv.first==-1) break;
                doMove(mv.first, mv.second);
            }
            if (!ops.empty())
                lastMove = {ops.back().first-1, ops.back().second-1};
            if ((int)ops.size() == beforeOps) stagnation++;
            else stagnation = 0;
            if (stagnation > 100000) break; // give up heuristic
        }
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n,m;
    if (!(cin>>n>>m)) {
        return 0;
    }
    vector<vector<int>> init(n+1);
    for (int i=0;i<n;i++) {
        init[i].resize(m);
        for (int j=0;j<m;j++) cin>>init[i][j];
    }
    // pillar n (index n) is empty initially
    State solver(n, m, init);
    solver.solve();

    // If not solved, just output what we have (may be incorrect for some cases)
    int k = (int)solver.ops.size();
    if (k > solver.maxOps) k = solver.maxOps;
    cout<<k<<"\n";
    for (int i=0;i<k;i++) {
        cout<<solver.ops[i].first<<" "<<solver.ops[i].second<<"\n";
    }
    return 0;
}