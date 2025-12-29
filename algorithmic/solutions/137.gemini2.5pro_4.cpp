#include <iostream>
#include <vector>
#include <string>

// This program generates a specific map for the "Kangaroos" problem.
// The map is a 20x20 grid with a "double-sided comb" structure.
// This structure is a tree, as required, and is designed to make it
// difficult for agents to congregate under random movements.
// It consists of a central horizontal "backbone" and many vertical "teeth"
// connected to it. This segregates agent movement: agents on the backbone
// primarily respond to L/R commands, while agents on teeth respond to U/D.
// Moving between these sections requires being at an intersection and receiving
// the appropriate command, which is unlikely to happen for all agents
// in a coordinated way with random commands. The numerous dead-ends also
// help trap agents, preventing them from easily gathering.

void solve() {
    int n = 20;
    int m = 20;

    std::cout << n << " " << m << std::endl;

    std::vector<std::string> map(n, std::string(m, '0'));

    // The backbone is placed on a central row. For n=20, row 9 is chosen.
    int backbone_row = n / 2 - 1;
    for (int j = 0; j < m; ++j) {
        map[backbone_row][j] = '1';
    }

    // The teeth are placed on every second column (even indices) to ensure they
    // do not connect to each other, maintaining the tree structure.
    for (int j = 0; j < m; ++j) {
        if (j % 2 == 0) {
            // Upper teeth, from the top of the grid down to the backbone.
            for (int i = 0; i < backbone_row; ++i) {
                map[i][j] = '1';
            }
            // Lower teeth, from below the backbone to the bottom of the grid.
            for (int i = backbone_row + 1; i < n; ++i) {
                map[i][j] = '1';
            }
        }
    }

    // Print the generated map to standard output.
    for (int i = 0; i < n; ++i) {
        std::cout << map[i] << std::endl;
    }
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    solve();

    return 0;
}