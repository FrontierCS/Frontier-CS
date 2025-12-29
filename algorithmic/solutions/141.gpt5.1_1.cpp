#include <bits/stdc++.h>
using namespace std;

char query(int c) {
    cout << "? " << c << endl;
    cout.flush();
    char x;
    if (!(cin >> x)) exit(0);
    return x;
}

void reset_friend() {
    cout << "R" << endl;
    cout.flush();
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, k;
    if (!(cin >> n >> k)) return 0;

    vector<int> reps;

    for (int i = 1; i <= n; ++i) {
        if (reps.empty()) {
            reps.push_back(i);
            continue;
        }

        bool isNew = true;

        if (k == 1) {
            // Compare with each representative individually
            for (int r : reps) {
                reset_friend();
                query(r); // ignore response
                char ans = query(i);
                if (ans == 'Y') {
                    isNew = false;
                    break;
                }
            }
        } else {
            int groupSize = k - 1;
            for (size_t pos = 0; pos < reps.size(); pos += groupSize) {
                reset_friend();
                size_t end = min(pos + (size_t)groupSize, reps.size());
                for (size_t j = pos; j < end; ++j) {
                    query(reps[j]); // ignore response
                }
                char ans = query(i);
                if (ans == 'Y') {
                    isNew = false;
                    break;
                }
            }
        }

        if (isNew) {
            reps.push_back(i);
        }
    }

    int d = (int)reps.size();
    cout << "! " << d << endl;
    cout.flush();
    return 0;
}