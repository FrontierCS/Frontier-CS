#include <iostream>
#include <vector>
#include <algorithm>
#include <random>
using namespace std;

int query(const vector<int>& v) {
    cout << "? " << v.size();
    for (int x : v) cout << " " << x;
    cout << endl;
    int ans;
    cin >> ans;
    return ans;
}

int main() {
    int N, M;
    cin >> N >> M;
    int L = N * M;
    vector<int> dangos(L);
    for (int i = 0; i < L; i++) dangos[i] = i + 1;
    
    // random shuffle to improve average performance
    random_device rd;
    mt19937 g(rd());
    shuffle(dangos.begin(), dangos.end(), g);
    
    vector<vector<int>> groups; // each group is a color class
    
    for (int d : dangos) {
        if (groups.empty()) {
            groups.push_back({d});
            continue;
        }
        int K = groups.size();
        int lo = 0, hi = K; // hi is exclusive, lo is the candidate index
        while (lo < hi) {
            int mid = (lo + hi) / 2;
            vector<int> qset;
            for (int i = 0; i <= mid; i++) {
                qset.push_back(groups[i][0]); // representative of each group
            }
            qset.push_back(d);
            int ans = query(qset);
            if (ans == mid + 1) {
                hi = mid;
            } else {
                lo = mid + 1;
            }
        }
        if (lo == K) {
            groups.push_back({d});
        } else {
            groups[lo].push_back(d);
        }
    }
    
    // Output the M sticks
    for (int j = 0; j < M; j++) {
        cout << "!";
        for (int i = 0; i < N; i++) {
            cout << " " << groups[i][j];
        }
        cout << endl;
    }
    
    return 0;
}