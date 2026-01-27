#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int r, c;
    if (!(cin >> r >> c)) return 0;
    vector<string> grid(r);
    for (int i = 0; i < r; ++i) cin >> grid[i];

    // Directions: 0=up,1=right,2=down,3=left
    int dr[4] = {-1, 0, 1, 0};
    int dc[4] = {0, 1, 0, -1};

    auto inb = [&](int i, int j){ return i>=0 && i<r && j>=0 && j<c; };

    struct State { int i,j,d; };
    vector<State> all;
    for (int i=0;i<r;i++){
        for (int j=0;j<c;j++){
            if (grid[i][j]=='.'){
                for (int d=0;d<4;d++){
                    all.push_back({i,j,d});
                }
            }
        }
    }

    int N = r*c*4;
    // Precompute distance to wall and step availability and transitions
    // Map (i,j,d) to index
    auto idx = [&](int i,int j,int d){ return ((i*c)+j)*4 + d; };
    int totalStates = r*c*4;
    vector<int> dist(totalStates, -1);
    vector<char> openCell(totalStates, 0);
    vector<char> stepOK(totalStates, 0);
    vector<int> turnLeft(totalStates, -1), turnRight(totalStates, -1), stepNext(totalStates, -1);

    for (int i=0;i<r;i++){
        for (int j=0;j<c;j++){
            for (int d=0; d<4; d++){
                int id = idx(i,j,d);
                if (grid[i][j] == '#') continue;
                openCell[id] = 1;
                // compute distance to wall in direction d
                int ni=i, nj=j;
                int cnt=0;
                while (true){
                    int ti = ni + dr[d], tj = nj + dc[d];
                    if (!inb(ti,tj) || grid[ti][tj]=='#') break;
                    cnt++;
                    ni=ti; nj=tj;
                }
                dist[id] = cnt;
                // step
                int si = i + dr[d], sj = j + dc[d];
                if (inb(si,sj) && grid[si][sj]=='.'){
                    stepOK[id] = 1;
                    stepNext[id] = idx(si,sj,d);
                }
                // turns
                turnLeft[id] = idx(i,j,(d+3)%4);
                turnRight[id] = idx(i,j,(d+1)%4);
            }
        }
    }

    // Candidate set: store ids
    vector<int> cand;
    cand.reserve(all.size());
    for (auto &s: all) {
        int id = idx(s.i,s.j,s.d);
        if (openCell[id]) cand.push_back(id);
    }

    auto safeStepForAll = [&](const vector<int>& S){
        for (int id : S) if (!stepOK[id]) return false;
        return !S.empty();
    };

    auto partitionCounts = [&](const vector<int>& S, const string& action)->unordered_map<int,int>{
        unordered_map<int,int> m;
        m.reserve(S.size()*2+1);
        if (action == "left") {
            for (int id: S) {
                int nid = turnLeft[id];
                m[dist[nid]]++;
            }
        } else if (action == "right") {
            for (int id: S) {
                int nid = turnRight[id];
                m[dist[nid]]++;
            }
        } else if (action == "step") {
            for (int id: S) {
                int nid = stepNext[id];
                m[dist[nid]]++;
            }
        }
        return m;
    };

    auto chooseAction = [&](const vector<int>& S)->string{
        string best = "left";
        int bestGroups = -1;
        long long bestBalance = LLONG_MAX; // minimize largest group to be more balanced
        vector<string> actions = {"left", "right"};
        if (safeStepForAll(S)) actions.push_back("step");
        for (auto &a : actions) {
            auto parts = partitionCounts(S, a);
            int groups = (int)parts.size();
            long long maxGroup = 0;
            for (auto &p: parts) maxGroup = max<long long>(maxGroup, p.second);
            // prefer more groups, tie-breaker smaller max group, then prefer step, then right, then left
            int pref = (a=="step")?2: (a=="right")?1:0;
            if (groups > bestGroups ||
                (groups == bestGroups && (maxGroup < bestBalance ||
                 (maxGroup == bestBalance && pref > ((best=="step")?2:(best=="right")?1:0))))) {
                bestGroups = groups;
                bestBalance = maxGroup;
                best = a;
            }
        }
        return best;
    };

    // Main interaction loop
    while (true) {
        int d;
        if (!(cin >> d)) break;
        if (d == -1) return 0;

        // Filter candidates by observed distance
        vector<int> nextCand;
        nextCand.reserve(cand.size());
        for (int id : cand) {
            if (openCell[id] && dist[id] == d) nextCand.push_back(id);
        }
        cand.swap(nextCand);

        if (cand.empty()) {
            cout << "no" << endl;
            cout.flush();
            return 0;
        }
        if (cand.size() == 1) {
            int id = cand[0];
            int i = (id/4)/c;
            int j = (id/4)%c;
            cout << "yes " << (i+1) << " " << (j+1) << endl;
            cout.flush();
            return 0;
        }

        // If both left and right give identical single-value partitions and step not safe for all -> impossible
        bool stepSafe = safeStepForAll(cand);
        auto pL = partitionCounts(cand, "left");
        auto pR = partitionCounts(cand, "right");
        bool leftSingle = (pL.size() == 1);
        bool rightSingle = (pR.size() == 1);
        if (!stepSafe && leftSingle && rightSingle) {
            // additionally, check if the single values are equal; if not, still turning will distinguish next round
            int vL = pL.begin()->first;
            int vR = pR.begin()->first;
            if (vL == vR) {
                cout << "no" << endl;
                cout.flush();
                return 0;
            }
        }

        string action = chooseAction(cand);
        cout << action << endl;
        cout.flush();

        // Update candidate states based on our issued action (for next observation)
        vector<int> updated;
        updated.reserve(cand.size());
        if (action == "left") {
            for (int id: cand) updated.push_back(turnLeft[id]);
        } else if (action == "right") {
            for (int id: cand) updated.push_back(turnRight[id]);
        } else if (action == "step") {
            // ensure safe step for all before issuing; but double-check
            if (!stepSafe) {
                // Fallback: avoid crashing; turn right
                cout << "right" << endl;
                cout.flush();
                updated.clear();
                for (int id: cand) updated.push_back(turnRight[id]);
            } else {
                for (int id: cand) updated.push_back(stepNext[id]);
            }
        }
        cand.swap(updated);
    }
    return 0;
}