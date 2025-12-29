#include <bits/stdc++.h>
using namespace std;

int main() {
    int R, H;
    cin >> R >> H;
    const int n = 1000;
    const int m = 40;
    uint64_t code[1000];
    bool good = false;
    int attempts = 0;
    while (!good) {
        srand(attempts++);
        for (int i = 0; i < n; i++) {
            uint64_t r1 = rand();
            uint64_t r2 = rand();
            code[i] = (r1 << 31) | r2;
            code[i] &= (1ULL << m) - 1;
        }
        set<uint64_t> s;
        good = true;
        for (int i = 0; i < n && good; i++) {
            for (int j = i; j < n && good; j++) {
                uint64_t orr = code[i] | code[j];
                if (s.count(orr)) {
                    good = false;
                } else {
                    s.insert(orr);
                }
            }
        }
        if (attempts > 100) {
            assert(false);
        }
    }
    for (int k = 0; k < m; k++) {
        vector<int> poss;
        for (int i = 0; i < n; i++) {
            if (code[i] & (1ULL << k)) {
                poss.push_back(i + 1);
            }
        }
        cout << "? " << poss.size();
        for (int p : poss) {
            cout << " " << p;
        }
        cout << endl;
    }
    cout.flush();
    cout << "@" << endl;
    cout.flush();
    int L;
    cin >> L;
    vector<int> res(m);
    for (int i = 0; i < m; i++) {
        cin >> res[i];
    }
    uint64_t observed = 0;
    for (int k = 0; k < m; k++) {
        if (res[k]) {
            observed |= (1ULL << k);
        }
    }
    int a = -1, b = -1;
    bool found = false;
    for (int i = 0; i < n; i++) {
        for (int j = i; j < n; j++) {
            if ((code[i] | code[j]) == observed) {
                a = i + 1;
                b = j + 1;
                found = true;
                break;
            }
        }
        if (found) break;
    }
    assert(found);
    cout << "! " << a << " " << b << endl;
    cout.flush();
    return 0;
}