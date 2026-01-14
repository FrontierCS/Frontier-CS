#include <bits/stdc++.h>
using namespace std;

int main() {
    int N;
    cin >> N;
    vector<pair<int, int>> answers;
    for(int a = 1; a <= N; a++) {
        int low = N + 1;
        int high = 2 * N;
        while(low < high) {
            int mid = (low + high) / 2;
            int k = mid - low + 1;
            cout << "Query " << 1 + k << " " << a;
            for(int i = low; i <= mid; i++) {
                cout << " " << i;
            }
            cout << endl;
            int res;
            cin >> res;
            if(res == k + 1) {
                low = mid + 1;
            } else {
                high = mid;
            }
        }
        int b = low;
        answers.push_back({a, b});
    }
    for(auto p : answers) {
        cout << "Answer " << p.first << " " << p.second << endl;
    }
    return 0;
}