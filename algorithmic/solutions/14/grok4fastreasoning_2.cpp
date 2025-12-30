#include <bits/stdc++.h>
using namespace std;

int main() {
    map<int, long long> seen;
    long long cum = 0;
    long long bb = 31623LL;
    cout << "walk 0" << endl;
    fflush(stdout);
    int label;
    cin >> label;
    seen[label] = cum;
    bool found = false;
    long long the_n;
    for (long long i = 1; i <= bb; i++) {
        cout << "walk 1" << endl;
        fflush(stdout);
        cin >> label;
        cum += 1;
        if (seen.count(label)) {
            the_n = cum - seen[label];
            found = true;
            break;
        }
        seen[label] = cum;
    }
    if (!found) {
        while (true) {
            cout << "walk " << bb << endl;
            fflush(stdout);
            cin >> label;
            cum += bb;
            if (seen.count(label)) {
                the_n = cum - seen[label];
                found = true;
                break;
            }
            seen[label] = cum;
        }
    }
    cout << "guess " << the_n << endl;
    fflush(stdout);
    return 0;
}