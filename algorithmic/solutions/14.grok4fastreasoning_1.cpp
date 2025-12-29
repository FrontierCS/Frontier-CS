#include <bits/stdc++.h>
using namespace std;

int main() {
    map<long long, long long> seen;
    long long cur_disp = 0;
    cout << "walk 0" << endl;
    long long current_label;
    cin >> current_label;
    seen[current_label] = 0;

    const long long K = 31623LL;
    bool found = false;
    long long candidate_n = -1LL;

    // baby steps
    for (long long i = 1; i <= K; ++i) {
        cout << "walk 1" << endl;
        long long label;
        cin >> label;
        cur_disp += 1;
        if (seen.find(label) != seen.end()) {
            long long old_disp = seen[label];
            candidate_n = cur_disp - old_disp;
            found = true;
            break;
        }
        seen[label] = cur_disp;
    }

    if (!found) {
        // giant steps
        long long J = K + 1;
        while (true) {
            cout << "walk " << J << endl;
            long long label;
            cin >> label;
            cur_disp += J;
            auto it = seen.find(label);
            if (it != seen.end()) {
                candidate_n = cur_disp - it->second;
                found = true;
                break;
            }
        }
    }

    cout << "guess " << candidate_n << endl;
    return 0;
}