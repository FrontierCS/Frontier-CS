#include <bits/stdc++.h>
using namespace std;

static int n;

static int ask(const vector<int>& pos) {
    cout << "? " << (int)pos.size();
    for (int x : pos) cout << " " << x;
    cout << "\n";
    cout.flush();
    int ans;
    if (!(cin >> ans)) exit(0);
    if (ans == -1) exit(0);
    return ans;
}

static void answer_perm(const vector<int>& p) {
    cout << "! ";
    for (int i = 1; i <= n; i++) {
        if (i > 1) cout << " ";
        cout << p[i];
    }
    cout << "\n";
    cout.flush();
    exit(0);
}

static bool build_subsets_for_mod(
    int m,
    const vector<int>& helperVals,
    const vector<int>& helperPos,
    vector<vector<int>>& subsetsBySumResid // size m, each vector has size (m-1)
) {
    int K = (int)helperVals.size();
    int s = m - 1;
    if (K < s) return false;

    vector<vector<char>> reachable(s + 1, vector<char>(m, 0));
    vector<vector<int>> parIdx(s + 1, vector<int>(m, -1));
    vector<vector<int>> parRes(s + 1, vector<int>(m, -1));

    reachable[0][0] = 1;

    for (int idx = 0; idx < K; idx++) {
        int v = ((helperVals[idx] % m) + m) % m;
        for (int c = min(s, idx + 1); c >= 1; c--) {
            for (int r = 0; r < m; r++) {
                if (!reachable[c - 1][r]) continue;
                int nr = (r + v) % m;
                if (reachable[c][nr]) continue;
                reachable[c][nr] = 1;
                parIdx[c][nr] = idx;
                parRes[c][nr] = r;
            }
        }
    }

    subsetsBySumResid.assign(m, {});
    for (int target = 0; target < m; target++) {
        if (!reachable[s][target]) return false;
        vector<int> chosenHelperIdx;
        chosenHelperIdx.reserve(s);
        int c = s, r = target;
        while (c > 0) {
            int idx = parIdx[c][r];
            int pr = parRes[c][r];
            if (idx < 0) return false;
            chosenHelperIdx.push_back(idx);
            r = pr;
            c--;
        }
        reverse(chosenHelperIdx.begin(), chosenHelperIdx.end());

        vector<int> pos;
        pos.reserve(s);
        for (int idx : chosenHelperIdx) pos.push_back(helperPos[idx]);
        subsetsBySumResid[target] = std::move(pos);
    }
    return true;
}

static void find_extremes(vector<int>& valAtPos, vector<int>& posOfVal) {
    vector<int> extremes;
    extremes.reserve(2);

    vector<int> all;
    all.reserve(n - 1);

    for (int i = 1; i <= n && (int)extremes.size() < 2; i++) {
        all.clear();
        for (int j = 1; j <= n; j++) if (j != i) all.push_back(j);
        int ans = ask(all);
        if (ans == 1) extremes.push_back(i);
    }

    if ((int)extremes.size() < 2) {
        // Should not happen for n>2
        exit(0);
    }

    // Arbitrarily set first found as value 1, second as value n.
    posOfVal[1] = extremes[0];
    posOfVal[n] = extremes[1];
    valAtPos[posOfVal[1]] = 1;
    valAtPos[posOfVal[n]] = n;
}

static int find_next_low_value_pos(int t, const vector<int>& valAtPos, int posN) {
    // Find position of value (t+1) using query that returns 1 iff candidate holds (t+1) or n.
    // Skip posN to avoid selecting n.
    vector<int> remain;
    remain.reserve(n);

    for (int i = 1; i <= n; i++) {
        if (i == posN) continue;
        if (valAtPos[i] != -1) continue; // already assigned
        remain.clear();
        for (int j = 1; j <= n; j++) {
            if (j == i) continue;
            int vj = valAtPos[j];
            if (vj != -1 && vj <= t) continue; // exclude known low values 1..t
            remain.push_back(j);
        }
        int ans = ask(remain);
        if (ans == 1) return i;
    }
    return -1;
}

static void solve_sequential_small() {
    vector<int> valAtPos(n + 1, -1);
    vector<int> posOfVal(n + 1, -1);

    find_extremes(valAtPos, posOfVal);

    int posN = posOfVal[n];

    // Find values 2..n-2 (if any)
    for (int t = 1; t <= n - 3; t++) {
        int p = find_next_low_value_pos(t, valAtPos, posN);
        if (p < 0) exit(0);
        valAtPos[p] = t + 1;
        posOfVal[t + 1] = p;
    }

    // The remaining unassigned position (not posN) must be n-1 (if n>=4)
    if (n >= 4) {
        int lastPos = -1;
        for (int i = 1; i <= n; i++) {
            if (i == posN) continue;
            if (valAtPos[i] == -1) {
                lastPos = i;
                break;
            }
        }
        if (lastPos != -1) {
            valAtPos[lastPos] = n - 1;
            posOfVal[n - 1] = lastPos;
        }
    }

    vector<int> p(n + 1);
    for (int i = 1; i <= n; i++) {
        if (valAtPos[i] == -1) exit(0);
        p[i] = valAtPos[i];
    }

    if (p[1] > n / 2) {
        for (int i = 1; i <= n; i++) p[i] = n + 1 - p[i];
    }
    answer_perm(p);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if (!(cin >> n)) return 0;

    if (n == 2) {
        vector<int> p(3);
        p[1] = 1; p[2] = 2;
        answer_perm(p);
    }

    if (n <= 60) {
        solve_sequential_small();
        return 0;
    }

    vector<int> valAtPos(n + 1, -1);
    vector<int> posOfVal(n + 1, -1);

    find_extremes(valAtPos, posOfVal);
    int posN = posOfVal[n];

    int L = min(18, n - 2); // find low values up to L (need room for n-2 at most)
    for (int t = 1; t <= L - 1; t++) {
        int p = find_next_low_value_pos(t, valAtPos, posN);
        if (p < 0) exit(0);
        valAtPos[p] = t + 1;
        posOfVal[t + 1] = p;
    }

    vector<int> mods = {2, 3, 5, 7, 11};

    auto build_all_mod_subsets = [&](int curL,
                                     vector<vector<vector<int>>>& subsetsPerMod) -> bool {
        vector<int> helperVals;
        vector<int> helperPos;

        helperVals.reserve(curL + 1);
        helperPos.reserve(curL + 1);
        for (int v = 1; v <= curL; v++) {
            helperVals.push_back(v);
            helperPos.push_back(posOfVal[v]);
        }
        helperVals.push_back(n);
        helperPos.push_back(posOfVal[n]);

        subsetsPerMod.clear();
        subsetsPerMod.resize(mods.size());
        for (size_t idx = 0; idx < mods.size(); idx++) {
            int m = mods[idx];
            vector<vector<int>> subsetsBySumResid;
            if (!build_subsets_for_mod(m, helperVals, helperPos, subsetsBySumResid)) return false;
            subsetsPerMod[idx] = std::move(subsetsBySumResid);
        }
        return true;
    };

    vector<vector<vector<int>>> subsetsPerMod;
    // Ensure subsets exist; if not, extend L as needed.
    while (true) {
        if (build_all_mod_subsets(L, subsetsPerMod)) break;
        if (L >= n - 2) break;
        L++;
        int p = find_next_low_value_pos(L - 1, valAtPos, posN);
        if (p < 0) exit(0);
        valAtPos[p] = L;
        posOfVal[L] = p;
    }

    // Determine values for all remaining positions using residues
    vector<int> residues(mods.size(), 0);

    for (int i = 1; i <= n; i++) {
        if (valAtPos[i] != -1) continue;

        for (size_t mi = 0; mi < mods.size(); mi++) {
            int m = mods[mi];
            bool found = false;
            for (int r = 0; r < m; r++) {
                int needSum = (m - r) % m; // helper sum mod m
                vector<int> q = subsetsPerMod[mi][needSum];
                q.push_back(i);
                int ans = ask(q);
                if (ans == 1) {
                    residues[mi] = r;
                    found = true;
                    break;
                }
            }
            if (!found) exit(0);
        }

        int foundVal = -1;
        for (int v = 1; v <= n; v++) {
            bool ok = true;
            for (size_t mi = 0; mi < mods.size(); mi++) {
                if (v % mods[mi] != residues[mi]) {
                    ok = false;
                    break;
                }
            }
            if (ok) {
                foundVal = v;
                break;
            }
        }
        if (foundVal < 0) exit(0);
        valAtPos[i] = foundVal;
    }

    vector<int> p(n + 1);
    for (int i = 1; i <= n; i++) {
        if (valAtPos[i] == -1) exit(0);
        p[i] = valAtPos[i];
    }

    // Enforce p1 <= n/2
    if (p[1] > n / 2) {
        for (int i = 1; i <= n; i++) p[i] = n + 1 - p[i];
    }

    answer_perm(p);
    return 0;
}