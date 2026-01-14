#include <iostream>
#include <vector>
#include <algorithm>

using namespace std;

int query(int pen) {
    cout << "0 " << pen << endl;
    int res;
    cin >> res;
    return res;
}

void solve() {
    int n;
    cin >> n;
    vector<int> alive;
    for (int i = 0; i < n; ++i) {
        alive.push_back(i);
    }
    while (alive.size() > 2) {
        int i = alive.front();
        int j = alive.back();
        // duel between i and j
        while (true) {
            int ri = query(i);
            if (ri == 0) {
                // i is empty -> i loses
                alive.erase(alive.begin());
                break;
            }
            int rj = query(j);
            if (rj == 0) {
                // j is empty -> j loses
                alive.pop_back();
                break;
            }
        }
    }
    cout << "1 " << alive[0] << " " << alive[1] << endl;
}

int main() {
    int t;
    cin >> t;
    while (t--) {
        solve();
    }
    return 0;
}