#include <bits/stdc++.h>
using namespace std;

struct Solver {
    int R, C;
    vector<string> grid;
    // dist[i][j][d]: number of open squares until a wall from (i,j) facing d
    // d: 0=up,1=right,2=down,3=left
    vector<int> dist; // flattened R*C*4
    vector<int> candidates; // list of candidate state ids: ((i*C+j)<<2)|dir

    inline int idx(int i, int j, int d) const {
        return ((i * C + j) << 2) | d;
    }
    inline void from_idx(int id, int &i, int &j, int &d) const {
        int t = id >> 2;
        d = id & 3;
        i = t / C;
        j = t % C;
    }
    inline bool inb(int i, int j) const {
        return (0 <= i && i < R && 0 <= j && j < C);
    }
    inline int dist_at(int id) const {
        return dist[id];
    }
    inline bool open(int i, int j) const {
        return inb(i,j) && grid[i][j] == '.';
    }
    void precompute_dist() {
        dist.assign(R*C*4, 0);
        static const int di[4] = {-1,0,1,0};
        static const int dj[4] = {0,1,0,-1};
        for (int i = 0; i < R; ++i) {
            for (int j = 0; j < C; ++j) {
                if (grid[i][j] != '.') continue;
                for (int d = 0; d < 4; ++d) {
                    int cnt = 0;
                    int ni = i + di[d], nj = j + dj[d];
                    while (inb(ni, nj) && grid[ni][nj] == '.') {
                        ++cnt;
                        ni += di[d];
                        nj += dj[d];
                    }
                    dist[idx(i,j,d)] = cnt;
                }
            }
        }
    }
    inline bool step_allowed_all() const {
        static const int di[4] = {-1,0,1,0};
        static const int dj[4] = {0,1,0,-1};
        for (int id : candidates) {
            int i,j,d;
            from_idx(id,i,j,d);
            int ni = i + di[d], nj = j + dj[d];
            if (!(inb(ni,nj) && grid[ni][nj] == '.')) return false;
        }
        return !candidates.empty();
    }
    inline int next_state(int id, int action) const {
        // action: 0=left,1=right,2=step
        static const int di[4] = {-1,0,1,0};
        static const int dj[4] = {0,1,0,-1};
        int i,j,d;
        from_idx(id,i,j,d);
        if (action == 0) { // left
            int nd = (d + 3) & 3;
            return idx(i,j,nd);
        } else if (action == 1) { // right
            int nd = (d + 1) & 3;
            return idx(i,j,nd);
        } else { // step
            int ni = i + di[d], nj = j + dj[d];
            // assume caller ensures it's open
            return idx(ni,nj,d);
        }
    }
    string choose_action() {
        // actions: left, right, step (if allowed for all)
        vector<int> actions = {0,1};
        bool stepAll = step_allowed_all();
        if (stepAll) actions.push_back(2);

        // For each action, compute distribution of next observation
        // and score by worst-case bucket size, then sum of squares, then prefer step
        int bestAct = actions[0];
        long long bestWorst = LLONG_MAX;
        long long bestSumSq = LLONG_MAX;
        int bestDistinct = -1;

        for (int a : actions) {
            unordered_map<int,int> cnt;
            cnt.reserve(candidates.size()*2+1);
            for (int id : candidates) {
                int nid = next_state(id, a);
                int o = dist_at(nid);
                ++cnt[o];
            }
            long long worst = 0;
            long long sumsq = 0;
            for (auto &p : cnt) {
                worst = max<long long>(worst, p.second);
                sumsq += 1LL * p.second * p.second;
            }
            int distinct = (int)cnt.size();

            // Minimize worst, then sumsq, then maximize distinct, then prefer step
            bool better = false;
            if (worst < bestWorst) better = true;
            else if (worst == bestWorst) {
                if (sumsq < bestSumSq) better = true;
                else if (sumsq == bestSumSq) {
                    if (distinct > bestDistinct) better = true;
                    else if (distinct == bestDistinct) {
                        // Prefer step over turns if tie
                        if (a == 2 && bestAct != 2) better = true;
                        else if (a != 2 && bestAct != 2) {
                            // tie between turns: prefer left (0) over right (1)
                            if (a < bestAct) better = true;
                        }
                    }
                }
            }
            if (better) {
                bestAct = a;
                bestWorst = worst;
                bestSumSq = sumsq;
                bestDistinct = distinct;
            }
        }

        if (bestAct == 2) return "step";
        if (bestAct == 0) return "left";
        return "right";
    }

    void run() {
        ios::sync_with_stdio(false);
        cin.tie(nullptr);

        if (!(cin >> R >> C)) return;
        grid.resize(R);
        for (int i = 0; i < R; ++i) cin >> grid[i];

        precompute_dist();

        // Initialize candidates: all open cells, all 4 directions
        candidates.clear();
        for (int i = 0; i < R; ++i)
            for (int j = 0; j < C; ++j)
                if (grid[i][j] == '.')
                    for (int d = 0; d < 4; ++d)
                        candidates.push_back(idx(i,j,d));

        while (true) {
            int dobs;
            if (!(cin >> dobs)) break;
            if (dobs == -1) return;

            // Filter by observation
            vector<int> nextC;
            nextC.reserve(candidates.size());
            for (int id : candidates) {
                if (dist_at(id) == dobs) nextC.push_back(id);
            }
            candidates.swap(nextC);

            if (candidates.empty()) {
                cout << "no" << endl << flush;
                return;
            }

            // Check if all candidates share same position
            int fi, fj, fd;
            from_idx(candidates[0], fi, fj, fd);
            bool same_pos = true;
            for (size_t k = 1; k < candidates.size(); ++k) {
                int i,j,d;
                from_idx(candidates[k], i, j, d);
                if (i != fi || j != fj) { same_pos = false; break; }
            }
            if (same_pos) {
                cout << "yes " << (fi+1) << " " << (fj+1) << endl << flush;
                return;
            }

            // Choose and output action
            string act = choose_action();
            cout << act << endl << flush;

            // Update candidates by applying the action (state transition)
            int a;
            if (act == "left") a = 0;
            else if (act == "right") a = 1;
            else a = 2;
            for (int &id : candidates) {
                id = next_state(id, a);
            }
        }
    }
};

int main() {
    Solver s;
    s.run();
    return 0;
}