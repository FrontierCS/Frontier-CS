#include <iostream>
#include <vector>
#include <algorithm>
#include <cassert>
using namespace std;

int query(const vector<int>& v) {
    cout << "? " << v.size();
    for (int x : v) cout << " " << x;
    cout << endl;
    int res;
    cin >> res;
    return res;
}

void answer(const vector<int>& v) {
    cout << "!";
    for (int x : v) cout << " " << x;
    cout << endl;
}

int main() {
    int N, M;
    cin >> N >> M;
    int total = N * M;
    vector<int> rem(total);
    for (int i = 0; i < total; i++) rem[i] = i + 1;

    int sticks_done = 0;
    while (sticks_done < M) {
        int t = M - sticks_done; // sticks remaining (including current)
        vector<int> stick;
        for (int k = 0; k < N; k++) {
            bool found = false;
            for (size_t idx = 0; idx < rem.size(); idx++) {
                int cand = rem[idx];
                if (find(stick.begin(), stick.end(), cand) != stick.end()) continue;
                // build query set: all rem except stick and cand
                vector<int> qset;
                for (int x : rem) {
                    if (x == cand) continue;
                    if (find(stick.begin(), stick.end(), x) != stick.end()) continue;
                    qset.push_back(x);
                }
                int res = query(qset);
                if (res == t - 1) {
                    stick.push_back(cand);
                    found = true;
                    break;
                } else if (res == t - 2) {
                    // cand is same color as someone in stick
                    continue;
                } else {
                    // unexpected, but fallback
                }
            }
            if (!found) {
                // fallback: pick first available not in stick
                for (int cand : rem) {
                    if (find(stick.begin(), stick.end(), cand) == stick.end()) {
                        stick.push_back(cand);
                        break;
                    }
                }
            }
        }
        answer(stick);
        // remove stick indices from rem
        vector<int> new_rem;
        for (int x : rem) {
            if (find(stick.begin(), stick.end(), x) == stick.end()) {
                new_rem.push_back(x);
            }
        }
        rem = new_rem;
        sticks_done++;
    }
    return 0;
}