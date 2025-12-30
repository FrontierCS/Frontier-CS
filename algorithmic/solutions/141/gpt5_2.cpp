#include <bits/stdc++.h>
using namespace std;

int n, k;

string ask(int c) {
    cout << "? " << c << endl;
    cout.flush();
    string s;
    if (!(cin >> s)) exit(0);
    return s;
}

void reset() {
    cout << "R" << endl;
    cout.flush();
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if (!(cin >> n >> k)) return 0;

    int g = k / 2;
    if (g <= 0) g = 1;

    vector<int> idx(n);
    iota(idx.begin(), idx.end(), 1);

    int m = (n + g - 1) / g;
    vector<vector<int>> groups(m);
    for (int i = 0; i < n; ++i) {
        groups[i / g].push_back(idx[i]);
    }

    vector<char> alive(n + 1, 1);

    // Remove duplicates within each group
    for (int gi = 0; gi < m; ++gi) {
        reset();
        for (int id : groups[gi]) {
            if (!alive[id]) continue;
            string res = ask(id);
            if (!res.empty() && res[0] == 'Y') {
                alive[id] = 0;
            }
        }
    }

    // Compare pairs of groups
    for (int i = 0; i < m; ++i) {
        for (int j = i + 1; j < m; ++j) {
            vector<int> A, B;
            for (int id : groups[i]) if (alive[id]) A.push_back(id);
            for (int id : groups[j]) if (alive[id]) B.push_back(id);
            if (A.empty() || B.empty()) continue;

            // Since g <= k/2, we can process entire B after A in one go
            reset();
            for (int id : A) {
                string _ = ask(id); // ignore
            }
            for (int id : B) {
                string res = ask(id);
                if (!res.empty() && res[0] == 'Y') {
                    alive[id] = 0;
                }
            }
        }
    }

    int d = 0;
    for (int i = 1; i <= n; ++i) if (alive[i]) ++d;

    cout << "! " << d << endl;
    cout.flush();
    return 0;
}