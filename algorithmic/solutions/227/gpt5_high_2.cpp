#include <bits/stdc++.h>
using namespace std;

vector<int> computeLISIndices(const vector<int>& P, const vector<char>& alive, int sign) {
    int n = (int)P.size();
    vector<int> tailsVal;
    vector<int> tailsIdx;
    vector<int> prev(n, -1);
    for (int i = 0; i < n; ++i) {
        if (!alive[i]) continue;
        int x = sign * P[i];
        auto it = lower_bound(tailsVal.begin(), tailsVal.end(), x);
        int pos = (int)(it - tailsVal.begin());
        if (pos == (int)tailsVal.size()) {
            tailsVal.push_back(x);
            tailsIdx.push_back(i);
        } else {
            tailsVal[pos] = x;
            tailsIdx[pos] = i;
        }
        if (pos > 0) prev[i] = tailsIdx[pos - 1];
    }
    vector<int> res;
    if (tailsIdx.empty()) return res;
    int idx = tailsIdx.back();
    while (idx != -1) {
        res.push_back(idx);
        idx = prev[idx];
    }
    reverse(res.begin(), res.end());
    return res;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n;
    if (!(cin >> n)) return 0;
    vector<int> P(n);
    for (int i = 0; i < n; ++i) cin >> P[i];

    vector<char> alive(n, 1);
    vector<int> color(n, -1);

    deque<int> incSlots = {0, 2}; // a, c
    deque<int> decSlots = {1, 3}; // b, d

    for (int step = 0; step < 4; ++step) {
        bool incPossible = !incSlots.empty();
        bool decPossible = !decSlots.empty();
        if (!incPossible && !decPossible) break;

        vector<int> incSet, decSet;
        if (incPossible && decPossible) {
            incSet = computeLISIndices(P, alive, +1);
            decSet = computeLISIndices(P, alive, -1);
            bool chooseInc = incSet.size() >= decSet.size();
            if (chooseInc) {
                int slot = incSlots.front(); incSlots.pop_front();
                for (int idx : incSet) {
                    color[idx] = slot;
                    alive[idx] = 0;
                }
            } else {
                int slot = decSlots.front(); decSlots.pop_front();
                for (int idx : decSet) {
                    color[idx] = slot;
                    alive[idx] = 0;
                }
            }
        } else if (incPossible) {
            incSet = computeLISIndices(P, alive, +1);
            int slot = incSlots.front(); incSlots.pop_front();
            for (int idx : incSet) {
                color[idx] = slot;
                alive[idx] = 0;
            }
        } else {
            decSet = computeLISIndices(P, alive, -1);
            int slot = decSlots.front(); decSlots.pop_front();
            for (int idx : decSet) {
                color[idx] = slot;
                alive[idx] = 0;
            }
        }
        bool anyAlive = false;
        for (int i = 0; i < n; ++i) if (alive[i]) { anyAlive = true; break; }
        if (!anyAlive && step < 3) {
            // Still need to allocate empty slots if any; continue loop to pop them
            continue;
        }
    }

    // Assign remaining elements arbitrarily to 'a' (slot 0)
    for (int i = 0; i < n; ++i) if (color[i] == -1) color[i] = 0;

    vector<vector<int>> out(4);
    for (int i = 0; i < n; ++i) {
        out[color[i]].push_back(P[i]);
    }

    cout << out[0].size() << " " << out[1].size() << " " << out[2].size() << " " << out[3].size() << "\n";
    for (int s = 0; s < 4; ++s) {
        for (int i = 0; i < (int)out[s].size(); ++i) {
            if (i) cout << " ";
            cout << out[s][i];
        }
        cout << "\n";
    }
    return 0;
}