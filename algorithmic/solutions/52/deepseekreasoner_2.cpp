#include <bits/stdc++.h>
using namespace std;

int n;
int cur_val[1005]; // value at position i, 0 if unknown
int cur_pos[1005]; // position of value i, 0 if unknown

int ask(int l, int r) {
    cout << "1 " << l << " " << r << endl;
    cout.flush();
    int x;
    cin >> x;
    return x;
}

void do_swap(int i, int j) {
    if (i == j) return;
    cout << "2 " << i << " " << j << endl;
    cout.flush();
    int tmp;
    cin >> tmp; // should be 1
    // update our knowledge
    int vi = cur_val[i];
    int vj = cur_val[j];
    cur_val[i] = vj;
    cur_val[j] = vi;
    if (vi != 0) cur_pos[vi] = j;
    if (vj != 0) cur_pos[vj] = i;
}

int main() {
    int l1, l2;
    cin >> n >> l1 >> l2;
    
    if (n == 1) {
        cout << "3 1" << endl;
        return 0;
    }
    
    // Step 1: find the two endpoints (positions of 1 and n)
    vector<int> endpoints;
    for (int i = 1; i <= n; ++i) {
        do_swap(i, n);
        int res = ask(1, n-1);
        if (res == 1) {
            endpoints.push_back(i);
        }
        do_swap(i, n); // restore
    }
    
    // Choose one endpoint as value 1
    int e1 = endpoints[0];
    do_swap(e1, 1);
    
    // Initialize: position 1 holds value 1
    for (int i = 1; i <= n; ++i) cur_val[i] = 0;
    cur_val[1] = 1;
    cur_pos[1] = 1;
    
    int candidate_start = 2;
    int candidate_end = n;
    int current_value = 1;
    
    for (int v = 1; v <= n-1; ++v) {
        // binary search for the position of value current_value+1
        int l = candidate_start, r = candidate_end;
        while (l < r) {
            int mid = (l + r) / 2;
            int fS = ask(candidate_start, mid);
            int fTotal = ask(1, mid);
            int delta = fS + 1 - fTotal;
            if (delta == 1) {
                r = mid;
            } else {
                l = mid + 1;
            }
        }
        int neighbor_pos = l;
        
        // Now we know the value at neighbor_pos is current_value+1
        cur_val[neighbor_pos] = current_value + 1;
        cur_pos[current_value + 1] = neighbor_pos;
        
        // Swap it to position 1
        do_swap(1, neighbor_pos);
        // Move the determined value (now at neighbor_pos) out of the candidate block
        if (neighbor_pos != candidate_end) {
            do_swap(neighbor_pos, candidate_end);
        }
        candidate_end--;
        current_value++;
    }
    
    // Output the final permutation
    cout << "3";
    for (int i = 1; i <= n; ++i) {
        cout << " " << cur_val[i];
    }
    cout << endl;
    cout.flush();
    
    return 0;
}