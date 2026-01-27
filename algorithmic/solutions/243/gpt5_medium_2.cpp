#include <bits/stdc++.h>
using namespace std;

struct Key {
    int o, l, r, s;
    bool operator==(const Key& other) const {
        return o==other.o && l==other.l && r==other.r && s==other.s;
    }
};
struct KeyHash {
    size_t operator()(Key const& k) const noexcept {
        size_t h = k.o;
        h = h*1315423911u + (size_t)k.l + 0x9e3779b97f4a7c15ull + (h<<6) + (h>>2);
        h = h*1315423911u + (size_t)k.r + 0x9e3779b97f4a7c15ull + (h<<6) + (h>>2);
        h = h*1315423911u + (size_t)(k.s+2) + 0x9e3779b97f4a7c15ull + (h<<6) + (h>>2);
        return h;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int r, c;
    if (!(cin >> r >> c)) return 0;
    vector<string> grid(r);
    for (int i = 0; i < r; ++i) cin >> grid[i];

    // Map open cells to indices
    vector<vector<int>> base(r, vector<int>(c, -1));
    int posCount = 0;
    for (int i = 0; i < r; ++i)
        for (int j = 0; j < c; ++j)
            if (grid[i][j] == '.') base[i][j] = posCount++;

    if (posCount == 0) return 0; // should not happen as per problem

    const int dx[4] = {-1, 0, 1, 0};
    const int dy[4] = {0, 1, 0, -1};

    // Precompute distances to walls for each open cell and direction
    vector<vector<array<int,4>>> dist(r, vector<array<int,4>>(c, {0,0,0,0}));
    int maxDist = 0;
    for (int i = 0; i < r; ++i) {
        for (int j = 0; j < c; ++j) {
            if (grid[i][j] != '.') continue;
            for (int d = 0; d < 4; ++d) {
                int x = i, y = j, k = 0;
                while (true) {
                    x += dx[d];
                    y += dy[d];
                    if (x < 0 || x >= r || y < 0 || y >= c || grid[x][y] == '#') break;
                    ++k;
                }
                dist[i][j][d] = k;
                if (k > maxDist) maxDist = k;
            }
        }
    }

    // Build states
    int S = posCount * 4;
    vector<int> outDist(S), L(S), Rr(S), Step(S), posi(S), posj(S);
    for (int i = 0; i < r; ++i) {
        for (int j = 0; j < c; ++j) {
            if (grid[i][j] != '.') continue;
            int b = base[i][j];
            for (int d = 0; d < 4; ++d) {
                int id = b*4 + d;
                posi[id] = i;
                posj[id] = j;
                outDist[id] = dist[i][j][d];
                L[id] = b*4 + ((d + 3) & 3);
                Rr[id] = b*4 + ((d + 1) & 3);
                if (outDist[id] > 0) {
                    int ni = i + dx[d], nj = j + dy[d];
                    int nb = base[ni][nj];
                    Step[id] = nb*4 + d;
                } else {
                    Step[id] = -1;
                }
            }
        }
    }

    // Compute observational equivalence classes (partition refinement)
    vector<int> part(S, -1), newPart(S, -1);
    {
        unordered_map<int,int> m;
        int cls = 0;
        for (int s = 0; s < S; ++s) {
            int o = outDist[s];
            auto it = m.find(o);
            if (it == m.end()) {
                m[o] = cls;
                part[s] = cls++;
            } else {
                part[s] = it->second;
            }
        }
        bool changed = true;
        while (changed) {
            changed = false;
            unordered_map<Key,int,KeyHash> mp;
            int ncls = 0;
            for (int s = 0; s < S; ++s) {
                Key k{outDist[s], part[L[s]], part[Rr[s]], (Step[s] == -1 ? -1 : part[Step[s]])};
                auto it = mp.find(k);
                if (it == mp.end()) {
                    mp.emplace(k, ncls);
                    newPart[s] = ncls++;
                } else {
                    newPart[s] = it->second;
                }
            }
            if (newPart != part) {
                part.swap(newPart);
                changed = true;
            }
        }
    }

    // Belief set initialization
    vector<int> B;
    B.reserve(S);
    for (int s = 0; s < S; ++s) B.push_back(s);

    vector<char> used(S, 0);

    auto apply_action = [&](const vector<int>& cur, char act)->vector<int> {
        vector<int> nxt;
        nxt.reserve(cur.size());
        // reset used flags for ids we will set
        // Since we don't know which will be set, clear whole used (S <= 40000 => OK)
        fill(used.begin(), used.end(), 0);
        for (int s : cur) {
            int t = -1;
            if (act == 'L') t = L[s];
            else if (act == 'R') t = Rr[s];
            else if (act == 'S') t = Step[s];
            if (t >= 0 && !used[t]) {
                used[t] = 1;
                nxt.push_back(t);
            }
        }
        return nxt;
    };

    auto worst_after = [&](const vector<int>& cur, char act)->int {
        vector<int> counts(maxDist + 1, 0);
        for (int s : cur) {
            int t = -1;
            if (act == 'L') t = L[s];
            else if (act == 'R') t = Rr[s];
            else if (act == 'S') t = Step[s];
            if (t >= 0) {
                int v = outDist[t];
                counts[v]++;
            }
        }
        int worst = 0;
        for (int v = 0; v <= maxDist; ++v) if (counts[v] > worst) worst = counts[v];
        return worst;
    };

    while (true) {
        int d;
        if (!(cin >> d)) return 0;
        if (d == -1) return 0;

        // Filter by observed distance
        vector<int> filtered;
        filtered.reserve(B.size());
        for (int s : B) if (outDist[s] == d) filtered.push_back(s);
        B.swap(filtered);

        if (B.empty()) {
            cout << "no" << endl;
            return 0;
        }

        // If unique position
        int pi0 = posi[B[0]], pj0 = posj[B[0]];
        bool samePos = true;
        for (int s : B) {
            if (posi[s] != pi0 || posj[s] != pj0) { samePos = false; break; }
        }
        if (samePos) {
            cout << "yes " << (pi0 + 1) << " " << (pj0 + 1) << endl;
            return 0;
        }

        // If impossible (all in one equivalence class and positions differ)
        int cls0 = part[B[0]];
        bool sameClass = true;
        for (int s : B) if (part[s] != cls0) { sameClass = false; break; }
        if (sameClass) {
            // positions already differ (checked above), so impossible
            cout << "no" << endl;
            return 0;
        }

        // Choose next action to minimize worst-case remaining candidates
        // Allowed actions: left, right, step if d > 0
        int bestWorst = INT_MAX;
        char bestAct = 'L';

        int wl = worst_after(B, 'L');
        bestWorst = wl;
        bestAct = 'L';

        int wr = worst_after(B, 'R');
        if (wr < bestWorst || (wr == bestWorst && bestAct != 'S')) {
            bestWorst = wr;
            bestAct = 'R';
        }

        if (d > 0) {
            int ws = worst_after(B, 'S');
            // prefer step on tie to progress
            if (ws < bestWorst || (ws == bestWorst)) {
                bestWorst = ws;
                bestAct = 'S';
            }
        }

        if (bestAct == 'L') {
            cout << "left" << endl;
        } else if (bestAct == 'R') {
            cout << "right" << endl;
        } else {
            cout << "step" << endl;
        }

        // Update belief set to after action
        B = apply_action(B, bestAct);
    }
}