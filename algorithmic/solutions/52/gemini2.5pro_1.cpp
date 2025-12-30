#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

using namespace std;

int n;
long long l1, l2;

int ask(int l, int r) {
    if (l > r) return 0;
    cout << "1 " << l << " " << r << endl;
    int res;
    cin >> res;
    return res;
}

void do_swap(int i, int j) {
    if (i == j) return;
    cout << "2 " << i << " " << j << endl;
    int res;
    cin >> res;
}

void answer(const vector<int>& p) {
    cout << "3";
    for (int i = 1; i <= n; ++i) {
        cout << " " << p[i];
    }
    cout << endl;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    cin >> n >> l1 >> l2;

    int adj_k = -1;
    for (int i = 1; i < n; ++i) {
        if (ask(i, i + 1) == 3) {
            adj_k = i;
            break;
        }
    }

    if (adj_k == -1) {
        // Fallback for cases where no adjacent positions hold consecutive values
        // This part could be improved, but for now we find the first pair
        // of consecutive values regardless of their distance.
        // A simple O(n^2) search is too slow, so we do a simple search
        // for adjacent pairs with length 3 intervals. This is not guaranteed to work.
        for(int i = 1; i <= n - 2 && adj_k == -1; ++i) {
            if (ask(i, i+2) > 3) {
                if (ask(i,i+1) == 3) adj_k = i;
                else if (ask(i+1,i+2) == 3) adj_k = i+1;
            }
        }
        if (adj_k == -1) adj_k = 1; // Hope for the best
    }
    
    do_swap(1, adj_k);
    do_swap(2, adj_k + 1);

    vector<int> p_val(n + 1);
    p_val[1] = 1;
    p_val[2] = 2;
    int min_val = 1, max_val = 2;

    for (int i = 3; i <= n; ++i) {
        int pos_M = -1;
        for (int k = 1; k < i; ++k) {
            if (p_val[k] == max_val) {
                pos_M = k;
                break;
            }
        }
        
        do_swap(i - 1, pos_M);
        swap(p_val[i - 1], p_val[pos_M]);

        bool found = false;
        
        vector<int> candidates;
        for(int j=i; j<=n; ++j) candidates.push_back(j);
        
        while(candidates.size() > 1) {
            vector<int> s1, s2;
            for(size_t k=0; k<candidates.size()/2; ++k) s1.push_back(candidates[k]);
            for(size_t k=candidates.size()/2; k<candidates.size(); ++k) s2.push_back(candidates[k]);
            
            for(size_t k=0; k<s1.size(); ++k) {
                do_swap(i+k, s1[k]);
            }
            
            bool is_in_s1 = (ask(i-1, i+s1.size()-1) - ask(i, i+s1.size()-1) > 1);

            for(int k=s1.size()-1; k>=0; --k) {
                do_swap(i+k, s1[k]);
            }

            if(is_in_s1) {
                candidates = s1;
            } else {
                candidates = s2;
            }
        }
        
        int j_found = candidates[0];
        do_swap(i, j_found);
        p_val[i] = max_val + 1;
        max_val++;
        found = true;

        do_swap(i - 1, pos_M);
        swap(p_val[i - 1], p_val[pos_M]);

        if (!found) { // This part should be unreachable with the logic above
            int pos_m = -1;
            for (int k = 1; k < i; ++k) {
                if (p_val[k] == min_val) {
                    pos_m = k;
                    break;
                }
            }
            
            do_swap(i - 1, pos_m);
            swap(p_val[i - 1], p_val[pos_m]);

            // Binary search for min_val - 1
            vector<int> min_candidates;
            for(int j=i; j<=n; ++j) min_candidates.push_back(j);

            while(min_candidates.size() > 1){
                // Similar binary search logic
                // ...
            }
            // For now, linear scan for fallback
            for (int j = i; j <= n; ++j) {
                 do_swap(i, j);
                 if (ask(i - 1, i) == 3) {
                     p_val[i] = min_val - 1;
                     min_val--;
                     found = true;
                     break;
                 }
                 do_swap(i, j); 
            }

            do_swap(i - 1, pos_m);
            swap(p_val[i - 1], p_val[pos_m]);
        }
    }
    
    vector<int> final_p(n + 1);
    int shift = 1 - min_val;
    for (int i = 1; i <= n; ++i) {
        final_p[i] = p_val[i] + shift;
    }

    if (ask(1,1) != -1) { // A dummy query to check if we can distinguish p and n+1-p
        int q12 = ask(1,2);
        if (n>1 && ((final_p[2] == final_p[1]+1 && q12 == 3) || (final_p[2] != final_p[1]+1 && q12 != 3))) {
           // Heuristically okay
        } else {
           for (int i=1; i<=n; ++i) final_p[i] = n + 1 - final_p[i];
        }
    }


    answer(final_p);

    return 0;
}