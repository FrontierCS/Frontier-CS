#include <bits/stdc++.h>
using namespace std;

static inline int lis_length_from_positions(const vector<int>& pos, const vector<int>& p, bool increasing) {
    vector<int> tails;
    tails.reserve(pos.size());
    for (int idx : pos) {
        int val = increasing ? p[idx] : -p[idx];
        auto it = lower_bound(tails.begin(), tails.end(), val);
        if (it == tails.end()) tails.push_back(val);
        else *it = val;
    }
    return (int)tails.size();
}

static inline vector<int> longest_subseq_indices(const vector<int>& rem, const vector<int>& p, bool increasing) {
    int m = (int)rem.size();
    vector<int> tailsVal;
    vector<int> tailsIdx;
    tailsVal.reserve(m);
    tailsIdx.reserve(m);
    vector<int> prevIdx(m, -1);

    for (int i = 0; i < m; ++i) {
        int val = increasing ? p[rem[i]] : -p[rem[i]];
        int j = int(lower_bound(tailsVal.begin(), tailsVal.end(), val) - tailsVal.begin());
        if (j == (int)tailsVal.size()) {
            tailsVal.push_back(val);
            tailsIdx.push_back(i);
        } else {
            tailsVal[j] = val;
            tailsIdx[j] = i;
        }
        if (j > 0) prevIdx[i] = tailsIdx[j - 1];
    }
    vector<int> res;
    if (!tailsIdx.empty()) {
        int idx = tailsIdx.back();
        while (idx != -1) {
            res.push_back(rem[idx]);
            idx = prevIdx[idx];
        }
        reverse(res.begin(), res.end());
    }
    return res;
}

struct PlanResult {
    vector<vector<int>> groups; // 0:a,1:b,2:c,3:d as positions
    long long score;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) {
        return 0;
    }
    vector<int> p(n);
    for (int i = 0; i < n; ++i) cin >> p[i];

    // group types: 0:a(LIS), 1:b(LDS), 2:c(LIS), 3:d(LDS)
    auto isIncreasingGroup = [](int g)->bool { return g == 0 || g == 2; };

    vector<vector<int>> orders = {
        {0,1,2,3}, // a,b,c,d
        {1,0,3,2}, // b,a,d,c
        {0,2,1,3}, // a,c,b,d
        {1,3,0,2}  // b,d,a,c
    };

    PlanResult best;
    best.score = -1;

    for (auto order : orders) {
        vector<vector<int>> groups(4);
        vector<int> rem(n);
        iota(rem.begin(), rem.end(), 0);

        for (int step = 0; step < 4; ++step) {
            int g = order[step];
            bool inc = isIncreasingGroup(g);
            vector<int> pick = longest_subseq_indices(rem, p, inc);
            groups[g] = pick;

            // Build next rem by removing picked indices
            vector<char> inPick(n, 0);
            for (int pos : pick) inPick[pos] = 1;
            vector<int> newRem;
            newRem.reserve(rem.size() - pick.size());
            for (int pos : rem) if (!inPick[pos]) newRem.push_back(pos);
            rem.swap(newRem);
        }

        vector<int> baseLen(4, 0);
        for (int g = 0; g < 4; ++g) baseLen[g] = (int)groups[g].size();

        // rem contains leftovers
        // Decide which group to assign leftovers to maximize improvement
        int bestGroupToAdd = 0;
        long long bestImprovement = LLONG_MIN;

        for (int g = 0; g < 4; ++g) {
            vector<int> unionPos = groups[g];
            unionPos.insert(unionPos.end(), rem.begin(), rem.end());
            sort(unionPos.begin(), unionPos.end());
            unionPos.erase(unique(unionPos.begin(), unionPos.end()), unionPos.end());

            int newLen = lis_length_from_positions(unionPos, p, isIncreasingGroup(g));
            long long improvement = (long long)newLen - baseLen[g];
            if (improvement > bestImprovement) {
                bestImprovement = improvement;
                bestGroupToAdd = g;
            }
        }

        long long totalScore = (long long)baseLen[0] + baseLen[1] + baseLen[2] + baseLen[3] + max(0LL, bestImprovement);

        if (totalScore > best.score) {
            best.score = totalScore;
            best.groups = groups;
            // assign leftovers to chosen group
            best.groups[bestGroupToAdd].insert(best.groups[bestGroupToAdd].end(), rem.begin(), rem.end());
        }
    }

    // Prepare output: sort each group's positions and print values
    for (int g = 0; g < 4; ++g) {
        sort(best.groups[g].begin(), best.groups[g].end());
    }

    int r = (int)best.groups[0].size();
    int s = (int)best.groups[1].size();
    int pc = (int)best.groups[2].size();
    int q = (int)best.groups[3].size();
    cout << r << " " << s << " " << pc << " " << q << "\n";

    for (int i = 0; i < r; ++i) {
        if (i) cout << " ";
        cout << p[best.groups[0][i]];
    }
    cout << "\n";
    for (int i = 0; i < s; ++i) {
        if (i) cout << " ";
        cout << p[best.groups[1][i]];
    }
    cout << "\n";
    for (int i = 0; i < pc; ++i) {
        if (i) cout << " ";
        cout << p[best.groups[2][i]];
    }
    cout << "\n";
    for (int i = 0; i < q; ++i) {
        if (i) cout << " ";
        cout << p[best.groups[3][i]];
    }
    cout << "\n";

    return 0;
}