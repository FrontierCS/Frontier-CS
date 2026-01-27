#include <bits/stdc++.h>
using namespace std;

struct State {
    int r, c, d; // row, col, dir
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int R, C;
    if (!(cin >> R >> C)) return 0;
    vector<string> grid(R);
    for (int i = 0; i < R; ++i) cin >> grid[i];

    auto inb = [&](int r, int c){ return r>=0 && r<R && c>=0 && c<C; };
    int dr[4] = {-1, 0, 1, 0};
    int dc[4] = {0, 1, 0, -1};

    // Map each open cell to index
    vector<pair<int,int>> open_cells;
    vector<vector<int>> idx(R, vector<int>(C, -1));
    for (int i = 0; i < R; ++i)
        for (int j = 0; j < C; ++j)
            if (grid[i][j] == '.') {
                idx[i][j] = (int)open_cells.size();
                open_cells.push_back({i,j});
            }
    if (open_cells.empty()) return 0;

    int Ncells = (int)open_cells.size();
    int N = Ncells * 4; // states = open cells * 4 directions

    auto sid = [&](int ci, int d){ return ci*4 + d; };
    auto cell_of_sid = [&](int s){ return s/4; };
    auto dir_of_sid = [&](int s){ return s%4; };

    // Precompute forward distances, successors, step validity
    vector<int> out_dist(N, 0);
    vector<int> succL(N, -1), succR(N, -1), succS(N, -1);
    vector<char> step_valid(N, 0);

    for (int ci = 0; ci < Ncells; ++ci) {
        int r = open_cells[ci].first;
        int c = open_cells[ci].second;
        for (int d = 0; d < 4; ++d) {
            int s = sid(ci, d);
            // compute distance to wall in direction d
            int rr = r, cc = c;
            int dist = 0;
            while (true) {
                rr += dr[d];
                cc += dc[d];
                if (!inb(rr, cc) || grid[rr][cc] == '#') break;
                dist++;
            }
            out_dist[s] = dist;
            // left, right
            int dl = (d+3)%4;
            int drt = (d+1)%4;
            succL[s] = sid(ci, dl);
            succR[s] = sid(ci, drt);
            // step
            if (dist >= 1) {
                int nr = r + dr[d], nc = c + dc[d];
                int nci = idx[nr][nc];
                if (nci >= 0) {
                    step_valid[s] = 1;
                    succS[s] = sid(nci, d);
                } else {
                    step_valid[s] = 0; // shouldn't happen as '.' ensures valid
                    succS[s] = -1;
                }
            } else {
                step_valid[s] = 0;
                succS[s] = -1;
            }
        }
    }

    // Compute equivalence classes of states under observations and transitions (with step validity)
    vector<int> cls(N, 0), ncls(N, 0);
    // initial partition by (out_dist, step_valid)
    {
        vector<pair<int,int>> key(N);
        for (int s = 0; s < N; ++s) key[s] = {out_dist[s], (int)step_valid[s]};
        vector<int> order(N);
        iota(order.begin(), order.end(), 0);
        sort(order.begin(), order.end(), [&](int a, int b){
            if (key[a].first != key[b].first) return key[a].first < key[b].first;
            return key[a].second < key[b].second;
        });
        int cur = 0;
        for (int i = 0; i < N; ++i) {
            if (i && key[order[i]] != key[order[i-1]]) cur++;
            cls[order[i]] = cur;
        }
    }
    bool changed = true;
    while (changed) {
        changed = false;
        // refine using tuple (out_dist, step_valid, cls[succL], cls[succR], cls[succS or -1])
        vector<tuple<int,int,int,int,int>> key(N);
        for (int s = 0; s < N; ++s) {
            int a = out_dist[s];
            int b = (int)step_valid[s];
            int cL = cls[succL[s]];
            int cR = cls[succR[s]];
            int cS = step_valid[s] ? cls[succS[s]] : -1;
            key[s] = make_tuple(a,b,cL,cR,cS);
        }
        vector<int> order(N);
        iota(order.begin(), order.end(), 0);
        sort(order.begin(), order.end(), [&](int x, int y){ return key[x] < key[y]; });
        int cur = 0;
        for (int i = 0; i < N; ++i) {
            if (i && key[order[i]] != key[order[i-1]]) cur++;
            ncls[order[i]] = cur;
        }
        if (ncls != cls) {
            cls.swap(ncls);
            changed = true;
        }
    }

    // Initialize candidates: all states
    vector<int> cand;
    cand.reserve(N);
    for (int s = 0; s < N; ++s) cand.push_back(s);

    auto print_and_flush = [&](const string &cmd){
        cout << cmd << "\n" << flush;
    };

    auto unique_positions = [&](const vector<int>& S)->vector<pair<int,int>>{
        vector<pair<int,int>> res;
        unordered_set<long long> seen;
        for (int s: S) {
            int ci = cell_of_sid(s);
            int r = open_cells[ci].first;
            int c = open_cells[ci].second;
            long long key = ((long long)r<<20) ^ c;
            if (seen.insert(key).second) res.push_back({r,c});
        }
        return res;
    };

    auto all_safe_step = [&](const vector<int>& S)->bool{
        for (int s: S) if (!step_valid[s]) return false;
        return true;
    };

    while (true) {
        int d;
        if (!(cin >> d)) break;
        if (d == -1) break;

        // filter by observation
        vector<int> newcand;
        newcand.reserve(cand.size());
        for (int s: cand) if (out_dist[s] == d) newcand.push_back(s);
        cand.swap(newcand);

        if (cand.empty()) {
            print_and_flush("no");
            return 0;
        }
        // if unique position
        auto poslist = unique_positions(cand);
        if (poslist.size() == 1) {
            int r = poslist[0].first + 1;
            int c = poslist[0].second + 1;
            cout << "yes " << r << " " << c << "\n" << flush;
            return 0;
        }
        // Check impossibility: all candidates in the same equivalence class (even across different positions)
        {
            int cl0 = cls[cand[0]];
            bool same = true;
            for (int s: cand) if (cls[s] != cl0) { same = false; break; }
            if (same) {
                // Multiple positions but same behavioral class -> impossible
                print_and_flush("no");
                return 0;
            }
        }

        // Choose action among left, right, step (if safe for all)
        struct Action { string name; int type; }; // 0=left,1=right,2=step
        vector<Action> actions;
        actions.push_back({"left",0});
        actions.push_back({"right",1});
        if (all_safe_step(cand)) actions.push_back({"step",2});

        int bestA = -1;
        int bestSplit = -1;
        for (int ai = 0; ai < (int)actions.size(); ++ai) {
            int type = actions[ai].type;
            unordered_set<int> distinct; distinct.reserve(cand.size()*2);
            for (int s: cand) {
                int ns = -1;
                if (type == 0) ns = succL[s];
                else if (type == 1) ns = succR[s];
                else ns = succS[s];
                // ns should be valid if action safe
                int od = out_dist[ns];
                distinct.insert(od);
            }
            int score = (int)distinct.size();
            // prefer more distinct, tie-breaker: prefer step, then left, then right
            if (score > bestSplit) {
                bestSplit = score;
                bestA = ai;
            } else if (score == bestSplit) {
                int prevType = actions[bestA].type;
                int curType = actions[ai].type;
                auto rank = [&](int t){ return (t==2?2:(t==0?1:0)); };
                if (rank(curType) > rank(prevType)) bestA = ai;
            }
        }

        if (bestA == -1) {
            // Should not happen; fallback to left
            bestA = 0;
        }

        string cmd = actions[bestA].name;
        print_and_flush(cmd);

        // transform candidates for next round
        vector<int> nextcand;
        nextcand.reserve(cand.size());
        int type = actions[bestA].type;
        for (int s: cand) {
            int ns = -1;
            if (type == 0) ns = succL[s];
            else if (type == 1) ns = succR[s];
            else {
                if (!step_valid[s]) { ns = -1; }
                else ns = succS[s];
            }
            if (ns != -1) nextcand.push_back(ns);
        }
        cand.swap(nextcand);
    }

    return 0;
}