#include <bits/stdc++.h>
using namespace std;

struct Signature {
    int a, b, c; // left, right, step (or -1 if not used)
    bool operator<(Signature const& other) const {
        if (a != other.a) return a < other.a;
        if (b != other.b) return b < other.b;
        return c < other.c;
    }
    bool operator==(Signature const& other) const {
        return a == other.a && b == other.b && c == other.c;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int r, c;
    if (!(cin >> r >> c)) return 0;
    vector<string> grid(r);
    for (int i = 0; i < r; ++i) cin >> grid[i];

    auto inb = [&](int i, int j){ return i >= 0 && i < r && j >= 0 && j < c; };

    // Precompute distances in each direction for each open cell
    vector<vector<int>> dN(r, vector<int>(c, 0)), dS(r, vector<int>(c, 0)), dE(r, vector<int>(c, 0)), dW(r, vector<int>(c, 0));
    for (int i = 0; i < r; ++i) {
        for (int j = 0; j < c; ++j) {
            if (grid[i][j] == '#') continue;
            if (i - 1 >= 0 && grid[i-1][j] == '.') dN[i][j] = dN[i-1][j] + 1;
            else dN[i][j] = 0;
        }
    }
    for (int i = r - 1; i >= 0; --i) {
        for (int j = 0; j < c; ++j) {
            if (grid[i][j] == '#') continue;
            if (i + 1 < r && grid[i+1][j] == '.') dS[i][j] = dS[i+1][j] + 1;
            else dS[i][j] = 0;
        }
    }
    for (int i = 0; i < r; ++i) {
        for (int j = c - 1; j >= 0; --j) {
            if (grid[i][j] == '#') continue;
            if (j + 1 < c && grid[i][j+1] == '.') dE[i][j] = dE[i][j+1] + 1;
            else dE[i][j] = 0;
        }
    }
    for (int i = 0; i < r; ++i) {
        for (int j = 0; j < c; ++j) {
            if (grid[i][j] == '#') continue;
            if (j - 1 >= 0 && grid[i][j-1] == '.') dW[i][j] = dW[i][j-1] + 1;
            else dW[i][j] = 0;
        }
    }

    auto id_of = [&](int i, int j, int dir){ return ((i * c + j) << 2) | dir; };
    auto pos_of = [&](int id){ int cc = (id >> 2); return cc; };
    auto dir_of = [&](int id){ return id & 3; };
    auto i_of = [&](int id){ return (id >> 2) / c; };
    auto j_of = [&](int id){ return (id >> 2) % c; };

    int Nstates = r * c * 4;
    vector<int> distAhead(Nstates, -1);
    vector<int> nextL(Nstates, -1), nextR(Nstates, -1), nextS(Nstates, -1);

    int di[4] = {-1, 0, 1, 0};
    int dj[4] = {0, 1, 0, -1};

    for (int i = 0; i < r; ++i) {
        for (int j = 0; j < c; ++j) {
            if (grid[i][j] == '#') continue;
            int d0 = dN[i][j];
            int d1 = dE[i][j];
            int d2 = dS[i][j];
            int d3 = dW[i][j];
            int ds[4] = {d0, d1, d2, d3};
            for (int dir = 0; dir < 4; ++dir) {
                int id = id_of(i, j, dir);
                distAhead[id] = ds[dir];
                int ldir = (dir + 3) & 3;
                int rdir = (dir + 1) & 3;
                nextL[id] = id_of(i, j, ldir);
                nextR[id] = id_of(i, j, rdir);
                if (ds[dir] > 0) {
                    int ni = i + di[dir], nj = j + dj[dir];
                    nextS[id] = id_of(ni, nj, dir);
                } else {
                    nextS[id] = -1;
                }
            }
        }
    }

    // Build list of valid states (open cells only)
    vector<int> stateList;
    stateList.reserve(Nstates);
    for (int id = 0; id < Nstates; ++id) {
        int i = i_of(id), j = j_of(id);
        if (grid[i][j] == '.') stateList.push_back(id);
    }

    // Partition refinement: blocks of observational equivalence
    // Initial partition by distAhead
    vector<int> blockId(Nstates, -1);
    vector<vector<int>> blocks;
    {
        unordered_map<int, int> d2block;
        d2block.reserve(128);
        for (int id : stateList) {
            int d = distAhead[id];
            auto it = d2block.find(d);
            if (it == d2block.end()) {
                int b = (int)blocks.size();
                d2block[d] = b;
                blocks.push_back(vector<int>());
                blocks.back().push_back(id);
                blockId[id] = b;
            } else {
                int b = it->second;
                blocks[b].push_back(id);
                blockId[id] = b;
            }
        }
    }

    bool changed = true;
    while (changed) {
        changed = false;
        vector<vector<int>> newBlocks;
        newBlocks.reserve(blocks.size());
        vector<int> newBlockId(Nstates, -1);

        for (auto &B : blocks) {
            if (B.empty()) continue;
            int any = B[0];
            int dval = distAhead[any];
            bool allowStep = (dval > 0);

            vector<pair<Signature, int>> vec;
            vec.reserve(B.size());
            for (int id : B) {
                Signature sig;
                sig.a = blockId[nextL[id]];
                sig.b = blockId[nextR[id]];
                if (allowStep) sig.c = blockId[nextS[id]];
                else sig.c = -1;
                vec.emplace_back(sig, id);
            }
            sort(vec.begin(), vec.end(), [](auto const& x, auto const& y){
                if (x.first.a != y.first.a) return x.first.a < y.first.a;
                if (x.first.b != y.first.b) return x.first.b < y.first.b;
                return x.first.c < y.first.c;
            });
            int start = 0;
            while (start < (int)vec.size()) {
                int end = start + 1;
                while (end < (int)vec.size() && !(vec[start].first < vec[end].first) && !(vec[end].first < vec[start].first)) {
                    ++end;
                }
                // create new block
                int nb = (int)newBlocks.size();
                newBlocks.push_back(vector<int>());
                newBlocks.back().reserve(end - start);
                for (int k = start; k < end; ++k) {
                    int id = vec[k].second;
                    newBlocks.back().push_back(id);
                    newBlockId[id] = nb;
                }
                if (end - start < (int)vec.size()) changed = true;
                start = end;
            }
        }
        blocks.swap(newBlocks);
        for (auto &B : blocks) {
            for (int id : B) blockId[id] = newBlockId[id];
        }
    }

    // Candidate states
    vector<int> candidates = stateList;

    auto all_same_position = [&](const vector<int>& S)->bool {
        if (S.empty()) return false;
        int p = pos_of(S[0]);
        for (int id : S) if (pos_of(id) != p) return false;
        return true;
    };

    auto impossible_to_determine = [&](const vector<int>& S)->bool {
        // If there exist two states with same blockId but different positions
        unordered_map<int, int> firstPos;
        firstPos.reserve(S.size()*2+1);
        for (int id : S) {
            int b = blockId[id];
            auto it = firstPos.find(b);
            int p = pos_of(id);
            if (it == firstPos.end()) firstPos[b] = p;
            else if (it->second != p) return true;
        }
        return false;
    };

    enum Action { ACT_NONE, ACT_LEFT, ACT_RIGHT, ACT_STEP };
    Action lastAction = ACT_NONE;
    bool firstRound = true;

    while (true) {
        int d;
        if (!(cin >> d)) return 0;
        if (d == -1) return 0;

        // Update candidates based on last action and new observation
        vector<int> newCand;
        newCand.reserve(candidates.size());
        if (firstRound) {
            for (int id : candidates) {
                if (distAhead[id] == d) newCand.push_back(id);
            }
            firstRound = false;
        } else {
            for (int id : candidates) {
                int nid = -1;
                if (lastAction == ACT_LEFT) nid = nextL[id];
                else if (lastAction == ACT_RIGHT) nid = nextR[id];
                else if (lastAction == ACT_STEP) nid = nextS[id];
                else nid = id;
                if (nid == -1) continue;
                if (distAhead[nid] == d) newCand.push_back(nid);
            }
        }
        candidates.swap(newCand);
        if (candidates.empty()) {
            // Should not happen; but terminate to avoid undefined behavior
            cout << "no" << endl;
            return 0;
        }

        // Check if position determined
        if (all_same_position(candidates)) {
            int p = pos_of(candidates[0]);
            int ii = p / c, jj = p % c;
            cout << "yes " << (ii + 1) << " " << (jj + 1) << endl;
            return 0;
        }

        // Check impossibility
        if (impossible_to_determine(candidates)) {
            cout << "no" << endl;
            return 0;
        }

        // Choose next action
        bool allowStep = (d > 0);
        // Evaluate actions
        struct ActInfo {
            Action a;
            int worst;
            int distinct;
        };
        vector<ActInfo> options;

        auto eval_action = [&](Action a)->ActInfo {
            unordered_map<int,int> count;
            count.reserve(candidates.size()*2+1);
            for (int id : candidates) {
                int nid = -1;
                if (a == ACT_LEFT) nid = nextL[id];
                else if (a == ACT_RIGHT) nid = nextR[id];
                else if (a == ACT_STEP) nid = nextS[id];
                else nid = id;
                int nd = distAhead[nid];
                count[nd]++;
            }
            int worst = 0;
            for (auto &kv : count) worst = max(worst, kv.second);
            ActInfo info;
            info.a = a;
            info.worst = worst;
            info.distinct = (int)count.size();
            return info;
        };

        ActInfo best;
        bool best_set = false;

        // left
        {
            ActInfo info = eval_action(ACT_LEFT);
            if (!best_set || info.worst < best.worst || (info.worst == best.worst && info.distinct > best.distinct)) {
                best = info; best_set = true;
            }
        }
        // right
        {
            ActInfo info = eval_action(ACT_RIGHT);
            if (!best_set || info.worst < best.worst || (info.worst == best.worst && info.distinct > best.distinct)) {
                best = info; best_set = true;
            }
        }
        // step if allowed
        if (allowStep) {
            ActInfo info = eval_action(ACT_STEP);
            if (!best_set || info.worst < best.worst || (info.worst == best.worst && info.distinct > best.distinct)) {
                best = info; best_set = true;
            }
        }

        if (!best_set) {
            // Fallback
            cout << "no" << endl;
            return 0;
        }

        // Output chosen action
        if (best.a == ACT_LEFT) {
            cout << "left" << endl;
            lastAction = ACT_LEFT;
        } else if (best.a == ACT_RIGHT) {
            cout << "right" << endl;
            lastAction = ACT_RIGHT;
        } else {
            cout << "step" << endl;
            lastAction = ACT_STEP;
        }
    }

    return 0;
}