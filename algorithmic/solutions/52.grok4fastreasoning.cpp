#include <bits/stdc++.h>
using namespace std;

int main() {
    int n, l1, l2;
    cin >> n >> l1 >> l2;
    vector<bool> connected(n);
    for(int i = 1; i < n; i++) {
        cout << 1 << " " << i << " " << i + 1 << endl;
        cout.flush();
        int x;
        cin >> x;
        connected[i - 1] = (x == 1);
    }
    vector<int> lengths;
    int start = 1;
    for(int i = 1; i < n; i++) {
        if (!connected[i - 1]) {
            lengths.push_back(i - start + 1);
            start = i + 1;
        }
    }
    lengths.push_back(n - start + 1);
    int kk = lengths.size();
    vector<int> assigned_block(kk);
    int loww = 1, highh = kk;
    bool take_low = true;
    for(int i = 0; i < kk; i++) {
        if (take_low) {
            assigned_block[i] = loww++;
        } else {
            assigned_block[i] = highh--;
        }
        take_low = !take_low;
    }
    vector<int> block_length(kk + 1, 0);
    for(int i = 0; i < kk; i++) {
        int b = assigned_block[i];
        block_length[b] = lengths[i];
    }
    vector<int> block_start(kk + 1, 0);
    int curr_val = 1;
    for(int j = 1; j <= kk; j++) {
        block_start[j] = curr_val;
        curr_val += block_length[j];
    }
    vector<int> pp(n + 1);
    int poss = 1;
    for(int i = 0; i < kk; i++) {
        int b = assigned_block[i];
        int stt = block_start[b];
        int lenn = lengths[i];
        for(int j = 0; j < lenn; j++) {
            pp[poss + j] = stt + j;
        }
        poss += lenn;
    }
    cout << 3;
    for(int i = 1; i <= n; i++) {
        cout << " " << pp[i];
    }
    cout << endl;
    cout.flush();
    return 0;
}