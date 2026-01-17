#include <iostream>
#include <string>
#include <vector>

void send_command(int p_stone, const std::string& side, int p_exit) {
    std::cout << p_stone << " " << side << " " << p_exit << std::endl;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int m;
    std::cin >> m;

    int discovered_chambers = 0;
    
    while (true) {
        std::string observation;
        std::cin >> observation;

        if (observation == "treasure") {
            break;
        }

        if (observation == "center") {
            // A new, unmarked chamber. We assign it a mark based on how many
            // chambers we've discovered so far. This provides up to 2*m unique marks.
            int k = discovered_chambers;
            
            std::string side_to_place;
            if ((k / m) % 2 == 0) {
                side_to_place = "left";
            } else {
                side_to_place = "right";
            }
            
            int passage_to_mark = k % m;

            // From a "center" chamber, passage numbering is random.
            // We command to place the stone at our chosen `passage_to_mark` offset
            // from a random reference passage, and exit through an arbitrary but
            // consistent passage (e.g., passage 0 relative to the random reference).
            send_command(passage_to_mark, side_to_place, 0);

            discovered_chambers++;
        } else { // observation is "left" or "right"
            // A previously visited chamber. We apply a uniform strategy to
            // cycle through its passages. The current marked passage is reference 0.
            // The command "1 <side> 1" moves the stone one passage clockwise and
            // exits through that new passage. Repeated visits will explore all
            // passages from this chamber.
            send_command(1, observation, 1);
        }
    }

    return 0;
}