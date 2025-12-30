#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <cassert>

bool in_device[86001];
int max_slice_idx;

// Helper to perform a query and update device state
int do_query(int x) {
    std::cout << "? " << x << std::endl;
    in_device[x] = !in_device[x];
    int r;
    std::cin >> r;
    return r;
}

// Helper to report a pair
void report_pair(int u, int v) {
    std::cout << "! " << u << " " << v << std::endl;
}

// Clears the device
void clear_device() {
    std::vector<int> to_remove;
    for(int i = 1; i <= max_slice_idx; ++i) {
        if (in_device[i]) {
            to_remove.push_back(i);
        }
    }
    for (int slice : to_remove) {
        do_query(slice);
    }
}

// Puts a set of slices into the device, returns final distinct count
int set_device_content(const std::vector<int>& slices) {
    clear_device();
    int r = 0;
    if (slices.empty()) return 0;
    for (int slice : slices) {
        r = do_query(slice);
    }
    return r;
}

void solve(std::vector<int>& slices);

// Given two sets A and B, where each a in A is paired with some b in B.
// This function finds all pairs.
void match(std::vector<int>& A, std::vector<int>& B) {
    if (A.empty()) {
        return;
    }
    if (A.size() == 1) {
        report_pair(A[0], B[0]);
        return;
    }

    std::vector<int> A1, A2;
    for (size_t i = 0; i < A.size(); ++i) {
        if (i < A.size() / 2) {
            A1.push_back(A[i]);
        } else {
            A2.push_back(A[i]);
        }
    }

    int r0 = set_device_content(A1);

    std::vector<int> B1, B2;
    for (int b : B) {
        int r1 = do_query(b);
        do_query(b); // Toggle back
        if (r1 == r0) {
            B1.push_back(b);
        } else {
            B2.push_back(b);
        }
    }

    match(A1, B1);
    match(A2, B2);
}

// Main recursive function to solve for a given set of slices
void solve(std::vector<int>& slices) {
    if (slices.size() <= 1) {
        return;
    }
    if (slices.size() == 2) {
        report_pair(slices[0], slices[1]);
        return;
    }

    std::vector<int> S1, S2;
    for (size_t i = 0; i < slices.size(); ++i) {
        if (i < slices.size() / 2) {
            S1.push_back(slices[i]);
        } else {
            S2.push_back(slices[i]);
        }
    }

    int r0_S2 = set_device_content(S2);
    
    std::vector<int> S1_in, S1_out;
    for (int s : S1) {
        int r1 = do_query(s);
        do_query(s);
        if (r1 == r0_S2) {
            S1_out.push_back(s);
        } else {
            S1_in.push_back(s);
        }
    }

    int r0_S1 = set_device_content(S1);
    
    std::vector<int> S2_in, S2_out;
    for (int s : S2) {
        int r1 = do_query(s);
        do_query(s);
        if (r1 == r0_S1) {
            S2_out.push_back(s);
        } else {
            S2_in.push_back(s);
        }
    }
    
    assert(S1_out.size() == S2_out.size());

    match(S1_out, S2_out);

    solve(S1_in);
    solve(S2_in);
}


int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int N;
    std::cin >> N;
    max_slice_idx = 2 * N;

    std::vector<int> all_slices(max_slice_idx);
    std::iota(all_slices.begin(), all_slices.end(), 1);
    
    for(int i = 0; i <= max_slice_idx; ++i) {
        in_device[i] = false;
    }

    solve(all_slices);

    return 0;
}