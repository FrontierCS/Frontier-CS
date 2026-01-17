#include <bits/stdc++.h>
using namespace std;

static vector<int> getLISIndices(const vector<int>& arr, const vector<char>& alive, bool inc) {
    int n = (int)arr.size();
    vector<int> parent(n, -1);
    vector<int> d; d.reserve(n);
    vector<int> pos; pos.reserve(n);

    auto val = [&](int i)->int {
        return inc ? arr[i] : -arr[i];
    };

    for (int i = 0; i < n; ++i) {
        if (!alive[i]) continue;
        int v = val(i);
        int j = int(lower_bound(d.begin(), d.end(), v) - d.begin());
        if (j == (int)d.size()) {
            d.push_back(v);
            pos.push_back(i);
        } else {
            d[j] = v;
            pos[j] = i;
        }
        if (j > 0) parent[i] = pos[j-1];
    }

    vector<int> seq;
    if (pos.empty()) return seq;
    int last = pos.back();
    while (last != -1) {
        seq.push_back(last);
        last = parent[last];
    }
    reverse(seq.begin(), seq.end());
    return seq;
}

static long long simulatePattern(const vector<int>& arr, const vector<int>& pattern) {
    int n = (int)arr.size();
    vector<char> alive(n, 1);
    long long score = 0;
    int incUsed = 0, decUsed = 0;
    for (int step = 0; step < (int)pattern.size(); ++step) {
        bool wantInc = (pattern[step] == 0);
        if (wantInc) {
            if (incUsed >= 2) continue;
            vector<int> seq = getLISIndices(arr, alive, true);
            score += (long long)seq.size();
            for (int idx : seq) alive[idx] = 0;
            incUsed++;
        } else {
            if (decUsed >= 2) continue;
            vector<int> seq = getLISIndices(arr, alive, false);
            score += (long long)seq.size();
            for (int idx : seq) alive[idx] = 0;
            decUsed++;
        }
        // Early exit if no alive left
        // Not necessary but can save some time in simulation
        // Count alive quickly
        // Optional
    }
    return score;
}

static long long simulateDynamic(const vector<int>& arr) {
    int n = (int)arr.size();
    vector<char> alive(n, 1);
    long long score = 0;
    int incUsed = 0, decUsed = 0;
    for (int step = 0; step < 4; ++step) {
        if (incUsed >= 2 && decUsed >= 2) break;

        int incLen = -1, decLen = -1;
        vector<int> incSeq, decSeq;

        if (incUsed < 2) {
            incSeq = getLISIndices(arr, alive, true);
            incLen = (int)incSeq.size();
        }
        if (decUsed < 2) {
            decSeq = getLISIndices(arr, alive, false);
            decLen = (int)decSeq.size();
        }

        bool chooseInc = false;
        if (incLen > decLen) chooseInc = true;
        else if (decLen > incLen) chooseInc = false;
        else {
            if (incUsed < 2) chooseInc = true;
            else chooseInc = false;
        }

        if (chooseInc && incUsed < 2) {
            score += incLen;
            for (int idx : incSeq) alive[idx] = 0;
            incUsed++;
        } else if (!chooseInc && decUsed < 2) {
            score += decLen;
            for (int idx : decSeq) alive[idx] = 0;
            decUsed++;
        } else {
            // No available picks of that type; try the other if possible
            if (incUsed < 2) {
                score += incLen;
                for (int idx : incSeq) alive[idx] = 0;
                incUsed++;
            } else if (decUsed < 2) {
                score += decLen;
                for (int idx : decSeq) alive[idx] = 0;
                decUsed++;
            }
        }

        // If no alive left, break
        // Optional early exit
    }
    return score;
}

static void buildAssignmentPattern(const vector<int>& arr, const vector<int>& pattern, vector<int>& color) {
    int n = (int)arr.size();
    vector<char> alive(n, 1);
    color.assign(n, -1);
    int incUsed = 0, decUsed = 0;
    int incGroups[2] = {0, 2}; // a, c
    int decGroups[2] = {1, 3}; // b, d

    for (int step = 0; step < (int)pattern.size(); ++step) {
        bool wantInc = (pattern[step] == 0);
        if (wantInc) {
            if (incUsed >= 2) continue;
            vector<int> seq = getLISIndices(arr, alive, true);
            int g = incGroups[incUsed];
            for (int idx : seq) { color[idx] = g; alive[idx] = 0; }
            incUsed++;
        } else {
            if (decUsed >= 2) continue;
            vector<int> seq = getLISIndices(arr, alive, false);
            int g = decGroups[decUsed];
            for (int idx : seq) { color[idx] = g; alive[idx] = 0; }
            decUsed++;
        }
    }

    // Assign remaining elements arbitrarily (round-robin)
    int g = 0;
    for (int i = 0; i < n; ++i) {
        if (color[i] == -1) {
            color[i] = g;
            g = (g + 1) & 3;
        }
    }
}

static void buildAssignmentDynamic(const vector<int>& arr, vector<int>& color) {
    int n = (int)arr.size();
    vector<char> alive(n, 1);
    color.assign(n, -1);
    int incUsed = 0, decUsed = 0;
    int incGroups[2] = {0, 2}; // a, c
    int decGroups[2] = {1, 3}; // b, d

    for (int step = 0; step < 4; ++step) {
        if (incUsed >= 2 && decUsed >= 2) break;

        int incLen = -1, decLen = -1;
        vector<int> incSeq, decSeq;

        if (incUsed < 2) {
            incSeq = getLISIndices(arr, alive, true);
            incLen = (int)incSeq.size();
        }
        if (decUsed < 2) {
            decSeq = getLISIndices(arr, alive, false);
            decLen = (int)decSeq.size();
        }

        bool chooseInc = false;
        if (incLen > decLen) chooseInc = true;
        else if (decLen > incLen) chooseInc = false;
        else {
            if (incUsed < 2) chooseInc = true;
            else chooseInc = false;
        }

        if (chooseInc && incUsed < 2) {
            int g = incGroups[incUsed];
            for (int idx : incSeq) { color[idx] = g; alive[idx] = 0; }
            incUsed++;
        } else if (!chooseInc && decUsed < 2) {
            int g = decGroups[decUsed];
            for (int idx : decSeq) { color[idx] = g; alive[idx] = 0; }
            decUsed++;
        } else {
            // fallback
            if (incUsed < 2) {
                int g = incGroups[incUsed];
                for (int idx : incSeq) { color[idx] = g; alive[idx] = 0; }
                incUsed++;
            } else if (decUsed < 2) {
                int g = decGroups[decUsed];
                for (int idx : decSeq) { color[idx] = g; alive[idx] = 0; }
                decUsed++;
            }
        }
    }

    // Assign remaining elements arbitrarily (round-robin)
    int g = 0;
    for (int i = 0; i < n; ++i) {
        if (color[i] == -1) {
            color[i] = g;
            g = (g + 1) & 3;
        }
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;
    vector<int> p(n);
    for (int i = 0; i < n; ++i) cin >> p[i];

    // Prepare patterns: 0 = inc, 1 = dec
    vector<vector<int>> patterns;
    patterns.push_back({0,0,1,1});
    patterns.push_back({0,1,0,1});
    patterns.push_back({0,1,1,0});
    patterns.push_back({1,1,0,0});
    patterns.push_back({1,0,1,0});
    patterns.push_back({1,0,0,1});

    long long bestScore = -1;
    int bestType = -1; // 0..5 for patterns, 6 for dynamic
    int bestIdx = -1;

    // Evaluate fixed patterns
    for (int i = 0; i < (int)patterns.size(); ++i) {
        long long sc = simulatePattern(p, patterns[i]);
        if (sc > bestScore) {
            bestScore = sc;
            bestType = 0; // pattern
            bestIdx = i;
        }
    }

    // Evaluate dynamic greedy
    {
        long long sc = simulateDynamic(p);
        if (sc > bestScore) {
            bestScore = sc;
            bestType = 1; // dynamic
            bestIdx = -1;
        }
    }

    vector<int> color(n, -1);
    if (bestType == 0) {
        buildAssignmentPattern(p, patterns[bestIdx], color);
    } else {
        buildAssignmentDynamic(p, color);
    }

    // Build groups
    vector<int> A, B, C, D;
    A.reserve(n); B.reserve(n); C.reserve(n); D.reserve(n);
    for (int i = 0; i < n; ++i) {
        if (color[i] == 0) A.push_back(p[i]);
        else if (color[i] == 1) B.push_back(p[i]);
        else if (color[i] == 2) C.push_back(p[i]);
        else if (color[i] == 3) D.push_back(p[i]);
        else {
            // fallback assign to A
            A.push_back(p[i]);
        }
    }

    cout << (int)A.size() << " " << (int)B.size() << " " << (int)C.size() << " " << (int)D.size() << "\n";
    for (int i = 0; i < (int)A.size(); ++i) {
        if (i) cout << " ";
        cout << A[i];
    }
    cout << "\n";
    for (int i = 0; i < (int)B.size(); ++i) {
        if (i) cout << " ";
        cout << B[i];
    }
    cout << "\n";
    for (int i = 0; i < (int)C.size(); ++i) {
        if (i) cout << " ";
        cout << C[i];
    }
    cout << "\n";
    for (int i = 0; i < (int)D.size(); ++i) {
        if (i) cout << " ";
        cout << D[i];
    }
    cout << "\n";

    return 0;
}