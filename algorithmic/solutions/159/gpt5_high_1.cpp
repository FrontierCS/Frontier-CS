#include <bits/stdc++.h>
using namespace std;

struct Operation {
    int x1,y1,x2,y2,x3,y3,x4,y4;
};

struct Candidate {
    int s0;
    int r1, r2; // r1 < r2
    int s2;
    int anchor; // 0 -> anchor r1, 1 -> anchor r2
    int p1x, p1y;
    long long weight;
};

int N, M;
int ccenter;

inline bool inGrid(int x, int y) {
    return 0 <= x && x < N && 0 <= y && y < N;
}

inline bool RS_to_XY(int r, int s, int &x, int &y) {
    if (((r + s) & 1) != 0) return false;
    x = (r + s) / 2;
    y = (r - s) / 2;
    return inGrid(x,y);
}

inline long long weightPoint(int x, int y) {
    long long dx = x - ccenter;
    long long dy = y - ccenter;
    return dx*dx + dy*dy + 1;
}

bool existsBetween(const vector<int>& vec, int a, int b) {
    if (a > b) swap(a,b);
    auto it = upper_bound(vec.begin(), vec.end(), a);
    if (it == vec.end()) return false;
    return (*it) < b;
}

bool intervalsOverlapPositive(const vector<pair<int,int>>& intervals, int a, int b) {
    if (a > b) swap(a,b);
    for (auto &pr: intervals) {
        int l = pr.first, r = pr.second;
        int L = max(l, a);
        int R = min(r, b);
        if (R > L) return true;
    }
    return false;
}

void addInterval(vector<pair<int,int>>& intervals, int a, int b) {
    if (a > b) swap(a,b);
    intervals.emplace_back(a,b);
}

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    cin >> N >> M;
    ccenter = (N - 1) / 2;

    vector<pair<int,int>> initPts(M);
    for(int i=0;i<M;i++){
        int x,y; cin >> x >> y;
        initPts[i] = {x,y};
    }

    // Occupancy grid
    vector<vector<char>> occ(N, vector<char>(N, 0));
    for (auto &p: initPts) occ[p.first][p.second] = 1;

    // r in [0..2N-2], s in [-(N-1)..(N-1)]
    int Rmax = 2*N - 1; // indices 0..2N-2
    int Smax = 2*N - 1; // s index 0..2N-2 with offset
    int soff = N - 1;

    // Build dynamic maps
    vector<vector<int>> curRToS(Rmax); // r -> list of s
    vector<vector<int>> curSToR(Smax); // s -> list of r

    for (auto &p: initPts) {
        int x = p.first, y = p.second;
        int r = x + y;
        int s = x - y;
        curRToS[r].push_back(s);
        curSToR[s + soff].push_back(r);
    }
    for (int r=0;r<Rmax-0;r++) {
        auto &v = curRToS[r];
        sort(v.begin(), v.end());
        v.erase(unique(v.begin(), v.end()), v.end());
    }
    for (int si=0; si<Smax; si++) {
        auto &v = curSToR[si];
        sort(v.begin(), v.end());
        v.erase(unique(v.begin(), v.end()), v.end());
    }

    // Used intervals per s and r for condition 3
    vector<vector<pair<int,int>>> usedS(Smax);
    vector<vector<pair<int,int>>> usedR(Rmax);

    vector<Operation> ops;

    auto generateCandidates = [&](vector<Candidate>& candList){
        candList.clear();

        // For each s-line, get adjacent pairs on that line
        for (int si = 0; si < Smax; si++) {
            int s0 = si - soff;
            auto &Rlist = curSToR[si];
            if ((int)Rlist.size() < 2) continue;
            for (int idx = 0; idx + 1 < (int)Rlist.size(); idx++) {
                int r1 = Rlist[idx];
                int r2 = Rlist[idx+1];
                if (r1 > r2) swap(r1, r2);

                // anchor r1
                {
                    auto &Slist_r1 = curRToS[r1];
                    auto it = lower_bound(Slist_r1.begin(), Slist_r1.end(), s0);
                    if (it != Slist_r1.end() && *it == s0) {
                        int pos = int(it - Slist_r1.begin());
                        // neighbors
                        if (pos - 1 >= 0) {
                            int s2 = Slist_r1[pos-1];
                            // Now target p1 at (r2, s2)
                            int px, py;
                            if (RS_to_XY(r2, s2, px, py) && !occ[px][py]) {
                                // Pre-check emptiness on initial/current sets
                                bool ok = true;
                                // r=r2, between s0 and s2
                                if (existsBetween(curRToS[r2], s0, s2)) ok = false;
                                // s=s2, between r1 and r2
                                if (existsBetween(curSToR[s2 + soff], r1, r2)) ok = false;
                                if (ok) {
                                    Candidate cd;
                                    cd.s0 = s0; cd.r1 = r1; cd.r2 = r2; cd.s2 = s2; cd.anchor = 0;
                                    cd.p1x = px; cd.p1y = py;
                                    cd.weight = weightPoint(px, py);
                                    candList.push_back(cd);
                                }
                            }
                        }
                        if (pos + 1 < (int)Slist_r1.size()) {
                            int s2 = Slist_r1[pos+1];
                            int px, py;
                            if (RS_to_XY(r2, s2, px, py) && !occ[px][py]) {
                                bool ok = true;
                                if (existsBetween(curRToS[r2], s0, s2)) ok = false;
                                if (existsBetween(curSToR[s2 + soff], r1, r2)) ok = false;
                                if (ok) {
                                    Candidate cd;
                                    cd.s0 = s0; cd.r1 = r1; cd.r2 = r2; cd.s2 = s2; cd.anchor = 0;
                                    cd.p1x = px; cd.p1y = py;
                                    cd.weight = weightPoint(px, py);
                                    candList.push_back(cd);
                                }
                            }
                        }
                    }
                }

                // anchor r2
                {
                    auto &Slist_r2 = curRToS[r2];
                    auto it = lower_bound(Slist_r2.begin(), Slist_r2.end(), s0);
                    if (it != Slist_r2.end() && *it == s0) {
                        int pos = int(it - Slist_r2.begin());
                        if (pos - 1 >= 0) {
                            int s2 = Slist_r2[pos-1];
                            int px, py;
                            if (RS_to_XY(r1, s2, px, py) && !occ[px][py]) {
                                bool ok = true;
                                if (existsBetween(curRToS[r1], s0, s2)) ok = false;
                                if (existsBetween(curSToR[s2 + soff], r1, r2)) ok = false;
                                if (ok) {
                                    Candidate cd;
                                    cd.s0 = s0; cd.r1 = r1; cd.r2 = r2; cd.s2 = s2; cd.anchor = 1;
                                    cd.p1x = px; cd.p1y = py;
                                    cd.weight = weightPoint(px, py);
                                    candList.push_back(cd);
                                }
                            }
                        }
                        if (pos + 1 < (int)Slist_r2.size()) {
                            int s2 = Slist_r2[pos+1];
                            int px, py;
                            if (RS_to_XY(r1, s2, px, py) && !occ[px][py]) {
                                bool ok = true;
                                if (existsBetween(curRToS[r1], s0, s2)) ok = false;
                                if (existsBetween(curSToR[s2 + soff], r1, r2)) ok = false;
                                if (ok) {
                                    Candidate cd;
                                    cd.s0 = s0; cd.r1 = r1; cd.r2 = r2; cd.s2 = s2; cd.anchor = 1;
                                    cd.p1x = px; cd.p1y = py;
                                    cd.weight = weightPoint(px, py);
                                    candList.push_back(cd);
                                }
                            }
                        }
                    }
                }
            }
        }

        // Sort by weight descending
        sort(candList.begin(), candList.end(), [](const Candidate& a, const Candidate& b){
            if (a.weight != b.weight) return a.weight > b.weight;
            if (a.p1x != b.p1x) return a.p1x < b.p1x;
            return a.p1y < b.p1y;
        });
    };

    auto attemptCandidate = [&](const Candidate& cd)->bool{
        int s0 = cd.s0;
        int r1 = cd.r1, r2 = cd.r2;
        int s2 = cd.s2;
        int anchorR = (cd.anchor == 0 ? r1 : r2);
        int otherR  = (cd.anchor == 0 ? r2 : r1);

        // Compute points
        int x1 = cd.p1x, y1 = cd.p1y; // p1 = (otherR, s2)
        if (!inGrid(x1,y1) || occ[x1][y1]) return false;

        int x2,y2,x3,y3,x4,y4;
        if (!RS_to_XY(anchorR, s2, x2, y2)) return false;
        if (!RS_to_XY(anchorR, s0, x3, y3)) return false;
        if (!RS_to_XY(otherR,  s0, x4, y4)) return false;
        if (!inGrid(x2,y2) || !inGrid(x3,y3) || !inGrid(x4,y4)) return false;
        if (!occ[x2][y2] || !occ[x3][y3] || !occ[x4][y4]) return false;

        // Condition 2: no other dots on perimeter
        // s = s0 edge between r1 and r2
        if (existsBetween(curSToR[s0 + soff], r1, r2)) return false;
        // s = s2 edge between r1 and r2 (p1 not included)
        if (existsBetween(curSToR[s2 + soff], r1, r2)) return false;
        // r = anchorR edge between s0 and s2
        if (existsBetween(curRToS[anchorR], s0, s2)) return false;
        // r = otherR edge between s0 and s2
        if (existsBetween(curRToS[otherR], s0, s2)) return false;

        // Condition 3: edges do not share positive-length segment with previously drawn
        int rmin = min(r1, r2), rmax = max(r1, r2);
        int smin = min(s0, s2), smax = max(s0, s2);
        if (intervalsOverlapPositive(usedS[s0 + soff], rmin, rmax)) return false;
        if (intervalsOverlapPositive(usedS[s2 + soff], rmin, rmax)) return false;
        if (intervalsOverlapPositive(usedR[anchorR], smin, smax)) return false;
        if (intervalsOverlapPositive(usedR[otherR], smin, smax)) return false;

        // Accept: add operation
        Operation op;
        // Order: p1 (otherR,s2) -> (anchorR,s2) -> (anchorR,s0) -> (otherR,s0)
        op.x1 = x1; op.y1 = y1;
        op.x2 = x2; op.y2 = y2;
        op.x3 = x3; op.y3 = y3;
        op.x4 = x4; op.y4 = y4;
        ops.push_back(op);

        // Update occupancy
        occ[x1][y1] = 1;
        // Update dynamic maps
        {
            auto &v1 = curRToS[otherR];
            auto it1 = lower_bound(v1.begin(), v1.end(), s2);
            if (it1 == v1.end() || *it1 != s2) v1.insert(it1, s2);
        }
        {
            auto &v2 = curSToR[s2 + soff];
            auto it2 = lower_bound(v2.begin(), v2.end(), otherR);
            if (it2 == v2.end() || *it2 != otherR) v2.insert(it2, otherR);
        }

        // Update used intervals
        addInterval(usedS[s0 + soff], rmin, rmax);
        addInterval(usedS[s2 + soff], rmin, rmax);
        addInterval(usedR[anchorR], smin, smax);
        addInterval(usedR[otherR], smin, smax);

        return true;
    };

    // Multi-pass: generate candidates from current state and apply greedily
    int maxPass = 2; // a few passes to consider newly added points
    for (int pass = 0; pass < maxPass; pass++) {
        vector<Candidate> candidates;
        generateCandidates(candidates);
        bool anyAccepted = false;
        for (const auto& cd : candidates) {
            if (attemptCandidate(cd)) {
                anyAccepted = true;
            }
        }
        if (!anyAccepted) break;
    }

    // Output
    cout << ops.size() << "\n";
    for (auto &op: ops) {
        cout << op.x1 << " " << op.y1 << " " << op.x2 << " " << op.y2 << " " 
             << op.x3 << " " << op.y3 << " " << op.x4 << " " << op.y4 << "\n";
    }

    return 0;
}