# TikTok export and attribution policy

Duet Conversation Studio treats TikTok as a distribution target, not as a permission bypass. The first integration is a local export profile and a manual-review credit packet. It does not automatically post, scrape, or import another creator’s TikTok video.

The Termux export profile produces a 1080×1920 vertical MP4 with H.264 video, AAC audio, `yuv420p`, and fast-start metadata. TikTok’s Content Posting API documentation lists MP4 + H.264 as a supported example and requires an approved app, authorized `video.publish` scope, and creator authorization for direct posting. Unaudited clients are restricted to private viewing mode, so direct posting is intentionally disabled in this milestone. [1]

Each TikTok packet carries the generation UUID, source hashes, a caption with supplied creator/video credits, and a reminder to use TikTok’s built-in Mention → Videos credit control. TikTok’s official help says a creator or video can be credited in the description or comment, and that up to three videos can be credited. [2]

A credit line does not establish permission. The export request requires an explicit `rights_confirmed: true` acknowledgment. TikTok’s copyright guidance says content that violates another party’s copyright is not allowed and recommends posting only content the user owns or has permission or another lawful basis to use. [3]

TikTok Duet permissions also remain controlled by TikTok. The source creator may allow Duet for everyone, mutual friends, or nobody, and can remove associated Duets. [4] The studio therefore preserves the source URL, creator handle, source hash, and user-supplied rights acknowledgment, but does not claim that a rendered file is an official TikTok Duet or that credit guarantees monetization.

The Creator Rewards Program has separate eligibility rules and excludes Duet or Stitch videos from its definition of original content. A TikTok-optimized export must not promise Creator Rewards eligibility or revenue. [5]

## Implementation boundary

- Local Termux: `POST /api/generations/{id}/export/tiktok` creates the MP4 and `.tiktok.json` packet.
- Online companion: exposes the same profile in its protocol contract but does not create an online MP4 until durable media storage and a render worker exist.
- Future direct posting: requires a separate consented TikTok developer integration, approved scopes, creator-info query, audit trail, and an explicit final confirmation before posting.

## References

[1]: https://developers.tiktok.com/doc/content-posting-api-get-started/ "TikTok Content Posting API Get Started - Direct Post"
[2]: https://support.tiktok.com/en/using-tiktok/creating-videos/credit-a-video "TikTok Credit a Video"
[3]: https://support.tiktok.com/en/safety-hc/account-and-user-safety/copyright "TikTok Copyright"
[4]: https://support.tiktok.com/en/account-and-privacy/account-privacy-settings/duets "TikTok Duets"
[5]: https://support.tiktok.com/en/business-and-creator/creator-rewards-program "TikTok Creator Rewards Program"
