#include <iostream>
#include <vector>
#include <set>
#include <algorithm>
#include <cassert>

using namespace std;

int N, M, L;

int query_exclude(const set<int>& exclude) {
    int k = L - (int)exclude.size();
    cout << "? " << k;
    for (int i = 1; i <= L; ++i) {
        if (exclude.find(i) == exclude.end()) {
            cout << " " << i;
        }
    }
    cout << endl;
    int ans;
    cin >> ans;
    return ans;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    cin >> N >> M;
    L = N * M;

    // Step 1: Build a reference stick S (one dango per color)
    vector<int> S;
    vector<bool> inS(L + 1, false);
    for (int i = 1; i <= L; ++i) {
        if ((int)S.size() == N) break;
        if (inS[i]) continue;
        if (S.empty()) {
            S.push_back(i);
            inS[i] = true;
            continue;
        }
        set<int> exclude;
        for (int x : S) exclude.insert(x);
        exclude.insert(i);
        int ans = query_exclude(exclude);
        // ans = M-1 if i is a new color, M-2 if i's color already in S
        if (ans == M - 1) {
            S.push_back(i);
            inS[i] = true;
        }
    }

    // Step 2: Classify all remaining dangos
    vector<int> rem;
    for (int i = 1; i <= L; ++i) {
        if (!inS[i]) rem.push_back(i);
    }

    vector<int> colorId(L + 1, -1);
    for (size_t idx = 0; idx < S.size(); ++idx) {
        colorId[S[idx]] = idx;
    }

    // If N == 1, all remaining dangos have the same color as the only one in S.
    if (N > 1) {
        for (int i : rem) {
            int low = 0, high = N - 1;
            while (low < high) {
                int mid = (low + high) / 2;
                set<int> exclude;
                for (int j = low; j <= mid; ++j) {
                    exclude.insert(S[j]);
                }
                exclude.insert(i);
                int ans = query_exclude(exclude);
                if (ans == M - 2) {
                    high = mid;
                } else {
                    low = mid + 1;
                }
            }
            colorId[i] = low;
        }
    } else {
        // N == 1, all dangos have color 0
        for (int i : rem) colorId[i] = 0;
    }

    //