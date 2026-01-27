#include <iostream>
#include <vector>
#include <algorithm>
#include <cmath>
#include <cstring>
using namespace std;

int n;
bool known[501];
vector<int> visited; // nodes visited in order during forward walk

// ask a query and return response
int ask(int u, int k, const vector<int>& S) {
    cout << "? " << u << " " << k << " " << S.size();
    for (int x : S) cout << " " << x;
    cout << endl;
    cout.flush();
    int ans;
    cin >> ans;
    return ans;
}

// binary search to find f(u) within a given candidate list
int binary_search(int u, const vector<int>& candidates) {
    int l = 0, r = candidates.size() - 1;
    while (l < r) {
        int mid = (l + r) / 2;
        vector<int> S;
        for (int i = l; i <= mid; ++i) S.push_back(candidates[i]);
        int ans = ask(u, 1, S);
        if (ans == 1) {
            r = mid;
        } else {
            l = mid + 1;
        }
    }
    return l;
}

int main() {
    cin >> n;
    memset(known, 0, sizeof(known));
    visited.clear();
    visited.push_back(1);
    known[1] = true;
    int u = 1;
    int cycle_start = -