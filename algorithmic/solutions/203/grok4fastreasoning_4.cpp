#include <bits/stdc++.h>
using namespace std;

int main() {
    int N;
    cin >> N;
    int total = 2 * N;
    vector<int> A;
    for (int k = 1; k <= total; k++) {
        set<int> rem;
        for (int x : A) rem.insert(x);
        rem.insert(k);
        vector<int> att;
        for (int j = 1; j <= total; j++) {
            if (rem.find(j) == rem.end()) att.push_back(j);
        }
        cout << "Query " << att.size();
        for (int x : att) cout << " " << x;
        cout << endl;
        int d;
        cin >> d;
        if (d == N) {
            A.push_back(k);
        }
    }
    vector<int> B;
    set<int> aset(A.begin(), A.end());
    for (int j = 1; j <= total; j++) {
        if (aset.find(j) == aset.end()) B.push_back(j);
    }
    vector<pair<int, int>> answers;
    for (int a : A) {
        vector<int> curr = B;
        while (curr.size() > 1) {
            int h = curr.size() / 2;
            vector<int> V(curr.begin(), curr.begin() + h);
            set<int> rem;
            rem.insert(a);
            for (int x : V) rem.insert(x);
            vector<int> att;
            for (int j = 1; j <= total; j++) {
                if (rem.find(j) == rem.end()) att.push_back(j);
            }
            cout << "Query " << att.size();
            for (int x : att) cout << " " << x;
            cout << endl;
            int d;
            cin >> d;
            if (d == N - 1) {
                curr = V;
            } else {
                curr = vector<int>(curr.begin() + h, curr.end());
            }
        }
        int p = curr[0];
        int first = min(a, p);
        int second = max(a, p);
        answers.emplace_back(first, second);
    }
    for (auto& pr : answers) {
        cout << "Answer " << pr.first << " " << pr.second << endl;
    }
    return 0;
}