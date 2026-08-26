import {
    setText
} from "./utils.js";


export class OtaView {

    updateVersion(
        softwareVersion
    ) {

        if (
            softwareVersion
        ) {

            setText(
                "ota-current-version",
                softwareVersion
            );
        }
    }
}